"""Paso a paso del laboratorio. No crea filas de Execution ni intentos."""

from __future__ import annotations

from django.conf import settings

from apps.billing.services import consume_execution
from apps.executions.live import advance, feed, publish, replace_session, signal_pause, signal_stop
from apps.language.services import diagnostic_payload
from apps.learning.live import LabRun, begin, peek_run
from apps.learning.services import load_workspace
from config.errors import DomainError
from language_core.block_adapter import Adapted, adapt_workspace
from language_core.debugger import DebugRejected, open_program
from language_core.grammar import STRICT
from language_core.runtime import Limits

_ACTIONS = {"step", "continue", "pause", "stop", "restart"}


def start_run(user, data: dict[str, object]) -> dict[str, object]:
    workspace = load_workspace(data)
    adapted = adapt_workspace(workspace)
    if adapted.program is None or any(item.severity == "error" for item in adapted.diagnostics):
        return _refused(adapted)
    consume_execution(user)
    if settings.EXECUTION_RUNNER == "redis":
        return _launch_lab(user.pk, adapted)
    session = open_program(adapted.program, adapted.source, adapted.diagnostics)
    live = begin(
        user.pk,
        session,
        adapted.program,
        adapted.source,
        tuple(adapted.diagnostics),
        _bindings(adapted),
    )
    publish(live, session.events)
    return _public(live)


def control_run(user, run_id: str, action: object) -> dict[str, object]:
    if not isinstance(action, str) or action not in _ACTIONS:
        raise DomainError("La orden no es válida.")
    if settings.EXECUTION_RUNNER == "redis":
        return _control_lab(user.pk, run_id, action)
    live = require_run(user, run_id)
    if action == "pause":
        signal_pause(live)
        return _public(live)
    if action == "stop":
        signal_stop(live)
    if action == "restart":
        session = open_program(live.program, live.source, live.origin)
        replace_session(live, session)
        return _public(live)
    try:
        advance(live, action)
    except DebugRejected as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    return _public(live)


def submit_run_input(user, run_id: str, text: object) -> dict[str, object]:
    if not isinstance(text, str):
        raise DomainError("El dato no es válido.")
    if len(text) > Limits.from_profile(STRICT).max_string_length:
        raise DomainError("El dato es demasiado largo.")
    if settings.EXECUTION_RUNNER == "redis":
        return _input_lab(user.pk, run_id, text)
    live = require_run(user, run_id)
    try:
        feed(live, text)
    except DebugRejected as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    return _public(live)


def read_run(user, run_id: str) -> dict[str, object]:
    """Estado actual, con la consola completa, para rellenar un hueco del canal."""
    if settings.EXECUTION_RUNNER == "redis":
        meta = _lab_meta(user.pk, run_id)
        from apps.executions.bus import fetch_state

        state = fetch_state(str(run_id))
        if state is None:
            raise DomainError(
                "La sesión de depuración ya no está en memoria. Vuelve a depurar.",
                code="conflict",
                status_code=409,
            )
        return _from_state(state, _text(meta.get("source")), _binding_rows(meta.get("bindings")))
    return _public(require_run(user, run_id))


def require_run(user, run_id: str) -> LabRun:
    live = peek_run(str(run_id))
    if live is None or live.user_id != user.pk:
        raise DomainError(
            "No se encontró esta pasada del laboratorio.",
            code="not_found",
            status_code=404,
        )
    return live


def _bindings(adapted: Adapted) -> list[dict[str, object]]:
    return [
        {"block_id": item.block_id, "line": item.line, "column": item.column}
        for item in adapted.bindings
    ]


def _refused(adapted: Adapted) -> dict[str, object]:
    return {
        "id": None,
        "status": "error",
        "scope": "",
        "line": None,
        "column": None,
        "output": "",
        "variables": {},
        "pending_input": None,
        "diagnostics": [diagnostic_payload(item) for item in adapted.diagnostics],
        "source": adapted.source,
        "bindings": _bindings(adapted),
        "event_cursor": 0,
    }


def _public(live: LabRun) -> dict[str, object]:
    snap = live.session.snapshot()
    line = snap["line"]
    column = snap["column"]
    output = snap["output"]
    variables = snap["variables"]
    pending = snap["pending_input"]
    return {
        "id": live.run_id,
        "status": snap["status"],
        "scope": snap["scope"] if isinstance(snap.get("scope"), str) else "",
        "line": line if isinstance(line, int) else None,
        "column": column if isinstance(column, int) else None,
        "output": output if isinstance(output, str) else "",
        "variables": variables if isinstance(variables, dict) else {},
        "pending_input": pending if isinstance(pending, dict) else None,
        "diagnostics": [diagnostic_payload(item) for item in live.session.diagnostics],
        "source": live.source,
        "bindings": live.bindings,
        "event_cursor": live.seq,
    }


def _launch_lab(user_id: int, adapted: Adapted) -> dict[str, object]:
    from apps.executions.bus import BusTimeout, drop_kind, launch

    drop_kind(user_id, "lab")
    bindings = _bindings(adapted)
    try:
        state = launch(
            user_id=user_id,
            source=adapted.source,
            profile={"profile_key": "strict"},
            breakpoints=set(),
            interactive=True,
            kind="lab",
            bindings=bindings,
        )
    except BusTimeout as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    return _from_state(state, adapted.source, bindings)


def _control_lab(user_id: int, run_id: str, action: str) -> dict[str, object]:
    from apps.executions.bus import BusRejected, BusTimeout, command, fetch_state, signal

    meta = _lab_meta(user_id, run_id)
    if action == "pause":
        signal(run_id, "pause")
        current = fetch_state(run_id) or {}
        current["id"] = run_id
        return _from_state(current, _text(meta.get("source")), _binding_rows(meta.get("bindings")))
    if action == "stop":
        signal(run_id, "stop")
    try:
        state = command(run_id, action)
    except BusTimeout as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    except BusRejected as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    return _from_state(state, _text(meta.get("source")), _binding_rows(meta.get("bindings")))


def _input_lab(user_id: int, run_id: str, text: str) -> dict[str, object]:
    from apps.executions.bus import BusRejected, BusTimeout, command

    meta = _lab_meta(user_id, run_id)
    try:
        state = command(run_id, "input", text=text)
    except BusTimeout as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    except BusRejected as exc:
        raise DomainError(exc.message, code="conflict", status_code=409) from exc
    return _from_state(state, _text(meta.get("source")), _binding_rows(meta.get("bindings")))


def _lab_meta(user_id: int, run_id: str) -> dict[str, object]:
    from apps.executions.bus import load_meta

    meta = load_meta(run_id)
    owner = None if meta is None else meta.get("user_id")
    if meta is None or owner != user_id or meta.get("kind") != "lab":
        raise DomainError(
            "No se encontró esta pasada del laboratorio.",
            code="not_found",
            status_code=404,
        )
    return meta


def _from_state(
    state: dict[str, object], source: str, bindings: list[dict[str, object]]
) -> dict[str, object]:
    line = state.get("line")
    column = state.get("column")
    output = state.get("output")
    variables = state.get("variables")
    pending = state.get("pending_input")
    diagnostics = state.get("diagnostics")
    scope = state.get("scope")
    cursor = state.get("event_cursor")
    return {
        "id": state.get("id"),
        "status": state.get("status"),
        "scope": scope if isinstance(scope, str) else "",
        "line": line if isinstance(line, int) else None,
        "column": column if isinstance(column, int) else None,
        "output": output if isinstance(output, str) else "",
        "variables": variables if isinstance(variables, dict) else {},
        "pending_input": pending if isinstance(pending, dict) else None,
        "diagnostics": diagnostics if isinstance(diagnostics, list) else [],
        "source": source,
        "bindings": bindings,
        "event_cursor": cursor if isinstance(cursor, int) else 0,
    }


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _binding_rows(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
