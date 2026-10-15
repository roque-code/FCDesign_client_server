"""Sesiones de depuración vivas en el proceso de desarrollo.

El generador no se guarda en PostgreSQL. Otro proceso no puede reanudarlo.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable, Iterator

from language_core.debugger import DebugSession
from runner.protocol import sse_frame

TERMINAL = {"completed", "error", "cancelled", "timeout"}

_LOCK = threading.Lock()
_SESSIONS: dict[str, LiveDebug] = {}


class LiveDebug:
    """Una ejecución con su generador, su historial de eventos y sus oyentes."""

    def __init__(self, user_id: int, session: DebugSession, interactive: bool = True) -> None:
        self.user_id = user_id
        self.session = session
        self.interactive = interactive
        self.events: list[dict[str, object]] = []
        self.subscribers: list[queue.Queue[dict[str, object] | None]] = []
        self.events_lock = threading.Lock()
        self.advance_lock = threading.Lock()
        self.busy = False
        self.seq = 0


def forget_user(user_id: int) -> None:
    with _LOCK:
        stale = [key for key, live in _SESSIONS.items() if live.user_id == user_id]
        for key in stale:
            _SESSIONS.pop(key).session.close()


def store(
    execution_id: str, user_id: int, session: DebugSession, *, interactive: bool = True
) -> LiveDebug:
    live = LiveDebug(user_id, session, interactive)
    publish(live, session.events)
    with _LOCK:
        _SESSIONS[execution_id] = live
    return live


def peek(execution_id: str) -> LiveDebug | None:
    with _LOCK:
        return _SESSIONS.get(execution_id)


def publish(live: LiveDebug, events: list[dict[str, object]]) -> None:
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


def advance(live: LiveDebug, action: str, breakpoints: set[int] | None = None) -> None:
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


def feed(live: LiveDebug, text: str) -> None:
    with live.advance_lock:
        live.busy = True
        try:
            _during(live, lambda: live.session.provide_input(text))
        finally:
            live.busy = False


def _during(live: LiveDebug, run: Callable[[], None]) -> None:
    """Publica la salida antes de una espera, para que la pantalla se actualice."""
    published = len(live.session.events)

    def flush() -> None:
        nonlocal published
        fresh = live.session.events[published:]
        published = len(live.session.events)
        if fresh:
            publish(live, fresh)

    live.session.flush = flush
    try:
        run()
        flush()
    finally:
        live.session.flush = None


def replace_session(live: LiveDebug, session: DebugSession) -> None:
    with live.advance_lock:
        live.session.close()
        live.session = session
        publish(live, session.events)


def signal_pause(live: LiveDebug) -> None:
    live.session.pause_requested = True


def signal_stop(live: LiveDebug) -> None:
    live.session.stop_requested = True
    cancel = getattr(live.session.interpreter, "cancellation", None)
    if cancel is not None:
        cancel.cancel()


def stream(live: LiveDebug, execution_id: str, after: int, *, once: bool) -> Iterator[str]:
    with live.events_lock:
        backlog = [event for event in live.events if _event_id(event) > after]
        follow = not once and live.session.status not in TERMINAL
        subscriber: queue.Queue[dict[str, object] | None] | None = None
        if follow:
            subscriber = queue.Queue()
            live.subscribers.append(subscriber)
    for event in backlog:
        yield _frame(event, execution_id)
        if event.get("event") in ("finished", "error", "cancelled"):
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
            yield _frame(incoming, execution_id)
            if incoming.get("event") in ("finished", "error", "cancelled"):
                return
    finally:
        with live.events_lock:
            if subscriber in live.subscribers:
                live.subscribers.remove(subscriber)


def _event_id(event: dict[str, object]) -> int:
    value = event.get("id", 0)
    return value if isinstance(value, int) else 0


def _frame(event: dict[str, object], execution_id: str) -> str:
    return sse_frame(event, execution_id)
