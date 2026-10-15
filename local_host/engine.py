"""Sesiones del depurador en este proceso. El sobre es el de runner.protocol."""

from __future__ import annotations

import queue
import threading
import uuid
from collections.abc import Callable, Iterator
from typing import Any

from language_core.block_adapter import adapt_workspace
from language_core.block_import import workspace_from_source
from language_core.debugger import DebugRejected, DebugSession, open_debug, open_program
from language_core.diagnostics import Diagnostic
from language_core.flowchart import build
from language_core.grammar import LanguageProfile, profile_from_mapping
from language_core.interpreter import compile_source
from language_core.runtime import Limits
from runner.protocol import TERMINAL_EVENTS, diagnostic_to_json, sse_frame

MAX_SOURCE = 64 * 1024
MAX_WORKSPACE = 256 * 1024
MAX_SESSIONS = 32
TERMINAL = frozenset({"completed", "error", "cancelled", "timeout"})
EDITOR_ACTIONS = frozenset(
    {"step", "step_in", "step_out", "continue", "pause", "stop", "restart", "breakpoints"}
)
LAB_ACTIONS = frozenset({"step", "continue", "pause", "stop", "restart"})


class HostError(Exception):
    def __init__(self, message: str, *, code: str = "invalid", status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


class _Live:
    def __init__(self, session: DebugSession, *, interactive: bool) -> None:
        self.public_id = ""
        self.session = session
        self.interactive = interactive
        self.events: list[dict[str, object]] = []
        self.subscribers: list[queue.Queue[dict[str, object] | None]] = []
        self.events_lock = threading.Lock()
        self.advance_lock = threading.Lock()
        self.busy = False
        self.seq = 0
        self.kind = "editor"
        self.source = ""
        self.profile: dict[str, object] = {}
        self.program: object = None
        self.origin: tuple[Diagnostic, ...] = ()
        self.bindings: list[dict[str, object]] = []


class Host:
    """Un proceso, varias sesiones. Las órdenes llegan por HTTP, no por Redis."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[str, _Live] = {}

    def validate(self, body: dict[str, Any]) -> dict[str, object]:
        source, profile = _source_and_profile(body)
        compiled = compile_source(source, profile)
        return {"diagnostics": [_diagnostic(item) for item in compiled.diagnostics]}

    def flowchart(self, body: dict[str, Any]) -> dict[str, object]:
        source, profile = _source_and_profile(body)
        compiled = compile_source(source, profile)
        diagnostics = [_diagnostic(item) for item in compiled.diagnostics]
        if compiled.program is None:
            return {"graph": None, "diagnostics": diagnostics}
        return {"graph": build(compiled.program).as_dict(), "diagnostics": diagnostics}

    def open_editor(self, body: dict[str, Any]) -> dict[str, object]:
        source, profile = _source_and_profile(body)
        marks = _lines(body.get("breakpoints"))
        interactive = bool(body.get("interactive"))
        session = open_debug(source, profile, marks)
        live = self._keep(session, interactive=interactive)
        live.kind = "editor"
        live.source = source
        live.profile = _profile_body(body.get("profile"))
        return _editor_view(live)

    def control_editor(self, session_id: str, body: dict[str, Any]) -> dict[str, object]:
        action = body.get("action")
        if not isinstance(action, str) or action not in EDITOR_ACTIONS:
            raise HostError("La orden no es válida.")
        live = self._require(session_id)
        marks = _lines(body.get("breakpoints")) if "breakpoints" in body else None
        if action == "pause":
            live.session.pause_requested = True
            return _editor_view(live)
        if action == "stop":
            _signal_stop(live)
        if action == "restart":
            kept = marks if marks is not None else set(live.session.breakpoints)
            fresh = open_debug(
                live.source,
                profile_from_mapping(_profile_name(live.profile), live.profile),
                kept,
            )
            _replace(live, fresh)
            return _editor_view(live)
        try:
            _advance(live, action, marks)
        except DebugRejected as exc:
            raise HostError(exc.message, code="conflict", status=409) from exc
        return _editor_view(live)

    def input_editor(self, session_id: str, body: dict[str, Any]) -> dict[str, object]:
        text = body.get("text")
        if not isinstance(text, str):
            raise HostError("El dato no es válido.")
        if len(text) > Limits.from_profile(profile_from_mapping("strict", {})).max_string_length:
            raise HostError("El dato es demasiado largo.")
        live = self._require(session_id)
        try:
            _feed(live, text)
        except DebugRejected as exc:
            raise HostError(exc.message, code="conflict", status=409) from exc
        return _editor_view(live)

    def inspect_editor(self, session_id: str, body: dict[str, Any]) -> dict[str, object]:
        live = self._require(session_id)
        name = body.get("name")
        start = body.get("start", 0)
        count = body.get("count", 24)
        if (
            not isinstance(name, str)
            or isinstance(start, bool)
            or not isinstance(start, int)
            or isinstance(count, bool)
            or not isinstance(count, int)
        ):
            raise HostError("El arreglo no es válido.")
        try:
            return live.session.inspect(name, start, count)
        except DebugRejected as exc:
            raise HostError(exc.message, code="conflict", status=409) from exc

    def read_editor(self, session_id: str) -> dict[str, object]:
        return _editor_view(self._require(session_id))

    def preview_lab(self, body: dict[str, Any]) -> dict[str, object]:
        adapted = adapt_workspace(_workspace(body))
        return {
            "source": adapted.source,
            "bindings": _bindings(adapted.bindings),
            "diagnostics": [_diagnostic(item) for item in adapted.diagnostics],
        }

    def import_lab(self, body: dict[str, Any]) -> dict[str, object]:
        source = body.get("source")
        if not isinstance(source, str):
            raise HostError("El archivo debe ser texto.")
        if len(source.encode("utf-8")) > MAX_SOURCE:
            raise HostError("El archivo supera 64 KiB.")
        imported = workspace_from_source(source)
        return {
            "workspace": imported.workspace,
            "diagnostics": [_diagnostic(item) for item in imported.diagnostics],
        }

    def open_lab(self, body: dict[str, Any]) -> dict[str, object]:
        workspace = _workspace(body)
        adapted = adapt_workspace(workspace)
        if adapted.program is None or any(item.severity == "error" for item in adapted.diagnostics):
            return _lab_refused(adapted.source, adapted.bindings, adapted.diagnostics)
        session = open_program(adapted.program, adapted.source, adapted.diagnostics)
        live = self._keep(session, interactive=True)
        live.kind = "lab"
        live.source = adapted.source
        live.program = adapted.program
        live.origin = tuple(adapted.diagnostics)
        live.bindings = _bindings(adapted.bindings)
        return _lab_view(live)

    def control_lab(self, session_id: str, body: dict[str, Any]) -> dict[str, object]:
        action = body.get("action")
        if not isinstance(action, str) or action not in LAB_ACTIONS:
            raise HostError("La orden no es válida.")
        live = self._require(session_id)
        if live.kind != "lab":
            raise HostError(
                "No se encontró esta pasada del laboratorio.", code="not_found", status=404
            )
        if action == "pause":
            live.session.pause_requested = True
            return _lab_view(live)
        if action == "stop":
            _signal_stop(live)
        if action == "restart":
            fresh = open_program(live.program, live.source, live.origin)
            _replace(live, fresh)
            return _lab_view(live)
        try:
            _advance(live, action, None)
        except DebugRejected as exc:
            raise HostError(exc.message, code="conflict", status=409) from exc
        return _lab_view(live)

    def input_lab(self, session_id: str, body: dict[str, Any]) -> dict[str, object]:
        text = body.get("text")
        if not isinstance(text, str):
            raise HostError("El dato no es válido.")
        if len(text) > Limits.from_profile(profile_from_mapping("strict", {})).max_string_length:
            raise HostError("El dato es demasiado largo.")
        live = self._require(session_id)
        if live.kind != "lab":
            raise HostError(
                "No se encontró esta pasada del laboratorio.", code="not_found", status=404
            )
        try:
            _feed(live, text)
        except DebugRejected as exc:
            raise HostError(exc.message, code="conflict", status=409) from exc
        return _lab_view(live)

    def read_lab(self, session_id: str) -> dict[str, object]:
        live = self._require(session_id)
        if live.kind != "lab":
            raise HostError(
                "No se encontró esta pasada del laboratorio.", code="not_found", status=404
            )
        return _lab_view(live)

    def stream(self, session_id: str, after: int, *, once: bool) -> Iterator[str]:
        live = self._require(session_id)
        return _stream(live, session_id, after, once=once)

    def _keep(self, session: DebugSession, *, interactive: bool) -> _Live:
        live = _Live(session, interactive=interactive)
        _publish(live, session.events)
        with self._lock:
            if len(self._sessions) >= MAX_SESSIONS:
                oldest = next(iter(self._sessions))
                dropped = self._sessions.pop(oldest)
                dropped.session.close()
            public_id = uuid.uuid4().hex
            live.public_id = public_id
            self._sessions[public_id] = live
        return live

    def _require(self, session_id: str) -> _Live:
        with self._lock:
            live = self._sessions.get(session_id)
        if live is None:
            raise HostError(
                "La sesión de depuración ya no está en memoria. Vuelve a depurar.",
                code="conflict",
                status=409,
            )
        return live


def session_id(live: _Live) -> str:
    return live.public_id


def _source_and_profile(body: dict[str, Any]) -> tuple[str, LanguageProfile]:
    source = body.get("source")
    if not isinstance(source, str):
        raise HostError("Falta el fuente.")
    if len(source.encode("utf-8")) > MAX_SOURCE:
        raise HostError("El algoritmo es demasiado largo.")
    profile_body = _profile_body(body.get("profile"))
    return source, profile_from_mapping(_profile_name(profile_body), profile_body)


def _profile_body(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return {}


def _profile_name(profile: dict[str, object]) -> str:
    name = profile.get("profile_key") or profile.get("name") or "strict"
    return name if isinstance(name, str) and name else "strict"


def _workspace(body: dict[str, Any]) -> dict[str, Any]:
    workspace = body.get("workspace")
    if not isinstance(workspace, dict):
        raise HostError("Falta el workspace.")
    import json

    if len(json.dumps(workspace, ensure_ascii=False).encode()) > MAX_WORKSPACE:
        raise HostError("El workspace es demasiado grande.")
    return workspace


def _lines(value: object) -> set[int]:
    if not isinstance(value, list):
        return set()
    return {
        item for item in value if isinstance(item, int) and not isinstance(item, bool) and item > 0
    }


def _diagnostic(item: Diagnostic) -> dict[str, object]:
    return diagnostic_to_json(item)


def _bindings(rows: object) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    if not isinstance(rows, tuple) and not isinstance(rows, list):
        return found
    for item in rows:
        block_id = getattr(item, "block_id", None)
        line = getattr(item, "line", None)
        column = getattr(item, "column", None)
        if isinstance(block_id, str) and isinstance(line, int) and isinstance(column, int):
            found.append({"block_id": block_id, "line": line, "column": column})
    return found


def _visible_diagnostics(rows: object) -> list[dict[str, object]]:
    if not isinstance(rows, tuple):
        return []
    return [
        _diagnostic(item)
        for item in rows
        if isinstance(item, Diagnostic) and item.severity in ("error", "warning")
    ]


def _editor_view(live: _Live) -> dict[str, object]:
    snap = live.session.snapshot()
    return {
        "id": session_id(live),
        "status": snap["status"],
        "output": snap["output"] if isinstance(snap["output"], str) else "",
        "instruction_count": (
            snap["instruction_count"] if isinstance(snap["instruction_count"], int) else 0
        ),
        "version_number": None,
        "pending_input": snap["pending_input"],
        "diagnostics": _visible_diagnostics(snap["diagnostics"]),
        "debug": live.interactive,
        "line": snap["line"],
        "column": snap["column"],
        "scope": snap["scope"] if isinstance(snap["scope"], str) else "",
        "variables": snap["variables"] if isinstance(snap["variables"], dict) else {},
        "call_stack": snap["call_stack"] if isinstance(snap["call_stack"], list) else [],
        "last_condition": snap["last_condition"],
        "breakpoints": snap["breakpoints"] if isinstance(snap["breakpoints"], list) else [],
        "event_cursor": live.seq,
    }


def _lab_view(live: _Live) -> dict[str, object]:
    snap = live.session.snapshot()
    line = snap["line"]
    column = snap["column"]
    output = snap["output"]
    variables = snap["variables"]
    pending = snap["pending_input"]
    return {
        "id": session_id(live),
        "status": snap["status"],
        "scope": snap["scope"] if isinstance(snap.get("scope"), str) else "",
        "line": line if isinstance(line, int) else None,
        "column": column if isinstance(column, int) else None,
        "output": output if isinstance(output, str) else "",
        "variables": variables if isinstance(variables, dict) else {},
        "pending_input": pending if isinstance(pending, dict) else None,
        "diagnostics": [_diagnostic(item) for item in live.session.diagnostics],
        "source": live.source,
        "bindings": live.bindings,
        "event_cursor": live.seq,
    }


def _lab_refused(
    source: str, bindings: object, diagnostics: tuple[Diagnostic, ...]
) -> dict[str, object]:
    return {
        "id": None,
        "status": "error",
        "scope": "",
        "line": None,
        "column": None,
        "output": "",
        "variables": {},
        "pending_input": None,
        "diagnostics": [_diagnostic(item) for item in diagnostics],
        "source": source,
        "bindings": _bindings(bindings),
        "event_cursor": 0,
    }


def _publish(live: _Live, events: list[dict[str, object]]) -> None:
    outgoing: list[dict[str, object]] = []
    with live.events_lock:
        subscribers = list(live.subscribers)
        for event in events:
            live.seq += 1
            stored = {**event, "id": live.seq}
            live.events.append(stored)
            outgoing.append(stored)
    for event in outgoing:
        for subscriber in subscribers:
            subscriber.put(event)


def _during(live: _Live, run: Callable[[], None]) -> None:
    published = len(live.session.events)

    def flush() -> None:
        nonlocal published
        fresh = live.session.events[published:]
        published = len(live.session.events)
        if fresh:
            _publish(live, fresh)

    live.session.flush = flush
    try:
        run()
        flush()
    finally:
        live.session.flush = None


def _advance(live: _Live, action: str, breakpoints: set[int] | None) -> None:
    with live.advance_lock:
        if action == "stop" and live.busy:
            return
        live.busy = True
        try:

            def run() -> None:
                if breakpoints is not None:
                    live.session.set_breakpoints(breakpoints)
                if action != "breakpoints":
                    live.session.command(action)

            _during(live, run)
        finally:
            live.busy = False


def _feed(live: _Live, text: str) -> None:
    with live.advance_lock:
        _during(live, lambda: live.session.provide_input(text))


def _replace(live: _Live, session: DebugSession) -> None:
    with live.advance_lock:
        live.session.close()
        live.session = session
        _publish(live, session.events)


def _signal_stop(live: _Live) -> None:
    live.session.stop_requested = True
    cancel = getattr(live.session.interpreter, "cancellation", None)
    if cancel is not None:
        cancel.cancel()


def _stream(live: _Live, execution_id: str, after: int, *, once: bool) -> Iterator[str]:
    with live.events_lock:
        backlog = [event for event in live.events if _event_id(event) > after]
        follow = not once and live.session.status not in TERMINAL
        subscriber: queue.Queue[dict[str, object] | None] | None = None
        if follow:
            subscriber = queue.Queue()
            live.subscribers.append(subscriber)
    for event in backlog:
        yield sse_frame(event, execution_id)
        if event.get("event") in TERMINAL_EVENTS:
            follow = False
    if not follow or subscriber is None:
        if subscriber is not None:
            with live.events_lock:
                if subscriber in live.subscribers:
                    live.subscribers.remove(subscriber)
        return
    try:
        while True:
            try:
                incoming = subscriber.get(timeout=15)
            except queue.Empty:
                yield ": keepalive\n\n"
                if live.session.status in TERMINAL:
                    return
                continue
            if incoming is None:
                return
            yield sse_frame(incoming, execution_id)
            if incoming.get("event") in TERMINAL_EVENTS:
                return
    finally:
        with live.events_lock:
            if subscriber in live.subscribers:
                live.subscribers.remove(subscriber)


def _event_id(event: dict[str, object]) -> int:
    value = event.get("id", 0)
    return value if isinstance(value, int) else 0
