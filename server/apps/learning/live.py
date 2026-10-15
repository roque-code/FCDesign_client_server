"""Pasadas del laboratorio vivas en el proceso de desarrollo.

No se guardan en PostgreSQL y no comparten la tabla de sesiones del editor.
"""

from __future__ import annotations

import threading
import uuid

from apps.executions.live import LiveDebug
from language_core.ast_nodes import Program
from language_core.debugger import DebugSession
from language_core.diagnostics import Diagnostic

_LOCK = threading.Lock()
_RUNS: dict[str, LabRun] = {}


class LabRun(LiveDebug):
    """Una pasada con el árbol, el texto de vista y los bloques de esa versión."""

    def __init__(
        self,
        run_id: str,
        user_id: int,
        session: DebugSession,
        program: Program,
        source: str,
        origin: tuple[Diagnostic, ...],
        bindings: list[dict[str, object]],
    ) -> None:
        super().__init__(user_id, session)
        self.run_id = run_id
        self.program = program
        self.source = source
        self.origin = origin
        self.bindings = bindings


def begin(
    user_id: int,
    session: DebugSession,
    program: Program,
    source: str,
    origin: tuple[Diagnostic, ...],
    bindings: list[dict[str, object]],
) -> LabRun:
    run_id = str(uuid.uuid4())
    live = LabRun(run_id, user_id, session, program, source, origin, bindings)
    with _LOCK:
        stale = [key for key, item in _RUNS.items() if item.user_id == user_id]
        for key in stale:
            _RUNS.pop(key).session.close()
        _RUNS[run_id] = live
    return live


def peek_run(run_id: str) -> LabRun | None:
    with _LOCK:
        return _RUNS.get(run_id)
