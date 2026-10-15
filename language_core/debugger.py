"""Conductor de la ejecución.

`drive` recorre hasta el final. `DebugSession` usa el mismo generador y se
detiene en pasos, llamadas y puntos de interrupción.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Generator
from typing import Any, Literal

from language_core.diagnostics import Diagnostic
from language_core.runtime import Cancellation, Cell, ExecutionResult, RuntimeEvent, format_array
from language_core.type_system import format_value

Status = Literal["completed", "error", "waiting_input", "cancelled", "timeout"]


def pause_for(seconds: float, cancellation: Cancellation | None = None) -> None:
    """Detiene el hilo el tiempo pedido. Stop corta la espera en el siguiente corte."""
    if seconds <= 0:
        return
    deadline = time.monotonic() + seconds
    while True:
        if cancellation is not None and cancellation.requested:
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(0.05, remaining))


def drive(
    generator: Generator[RuntimeEvent, str, None],
    inputs: list[str],
    prior: tuple[Diagnostic, ...],
    variables_of: dict[str, Cell],
) -> ExecutionResult:
    """Consume los eventos y devuelve el resultado visible."""
    queue = list(inputs)
    diagnostics = list(prior)
    output: list[str] = []
    status: Status = "completed"
    pending: dict[str, str] | None = None
    event = _first(generator)
    while event is not None:
        if event.kind == "line":
            event = _next(generator)
            continue
        if event.kind == "output":
            text = event.payload.get("text", "")
            if isinstance(text, str):
                output.append(text)
            event = _next(generator)
            continue
        if event.kind == "clear":
            output.clear()
            event = _next(generator)
            continue
        if event.kind == "delay":
            raw = event.payload.get("seconds", 0)
            pause_for(raw if isinstance(raw, int | float) and not isinstance(raw, bool) else 0)
            event = _next(generator)
            continue
        if event.kind == "warning":
            diagnostic = event.payload.get("diagnostic")
            if isinstance(diagnostic, Diagnostic):
                diagnostics.append(diagnostic)
            event = _next(generator)
            continue
        if event.kind == "input_rejected":
            diagnostic = event.payload.get("diagnostic")
            if isinstance(diagnostic, Diagnostic):
                diagnostics.append(diagnostic)
            event = _next(generator)
            continue
        if event.kind == "input_requested":
            if not queue:
                status = "waiting_input"
                name = event.payload.get("name", "")
                type_name = event.payload.get("type", "")
                pending = {
                    "name": name if isinstance(name, str) else "",
                    "type": type_name if isinstance(type_name, str) else "",
                }
                break
            event = _send(generator, queue.pop(0))
            continue
        if event.kind == "error":
            diagnostic = event.payload.get("diagnostic")
            if isinstance(diagnostic, Diagnostic):
                diagnostics.append(diagnostic)
                status = "timeout" if diagnostic.code == "E0411" else "error"
            else:
                status = "error"
            break
        if event.kind == "cancelled":
            diagnostic = event.payload.get("diagnostic")
            if isinstance(diagnostic, Diagnostic):
                diagnostics.append(diagnostic)
            status = "cancelled"
            break
        if event.kind == "finished":
            status = "completed"
            break
        event = _next(generator)
    generator.close()
    variables: dict[str, str] = {}
    for name, cell in variables_of.items():
        if cell.array is not None:
            variables[name] = format_array(cell.array)
            continue
        if cell.value is None:
            continue
        variables[name] = format_value(cell.value.type_name, cell.value.value)
    return ExecutionResult(status, "".join(output), tuple(diagnostics), variables, pending)


DebugStatus = Literal["paused", "waiting_input", "completed", "error", "cancelled", "timeout"]
StepMode = Literal["step", "step_in", "step_out", "continue"]
Frame = dict[str, object]


class DebugRejected(Exception):
    """La orden no corresponde al estado de la sesión."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def executable_lines(program: object) -> set[int]:
    """Líneas donde empieza una sentencia. Un punto fuera de aquí no detiene."""
    from language_core.ast_nodes import (
        ForStmt,
        IfStmt,
        Program,
        RepeatStmt,
        SwitchStmt,
        WhileStmt,
    )

    if not isinstance(program, Program):
        return set()
    found: set[int] = set()

    def walk(statements: tuple[object, ...]) -> None:
        for statement in statements:
            span = getattr(statement, "span", None)
            if span is not None:
                found.add(span.start_line)
            if isinstance(statement, IfStmt):
                walk(statement.then_body)
                if statement.else_body is not None:
                    walk(statement.else_body)
            elif isinstance(statement, (WhileStmt, RepeatStmt, ForStmt)):
                walk(statement.body)
            elif isinstance(statement, SwitchStmt):
                for case in statement.cases:
                    walk(case.body)
                if statement.default_body is not None:
                    walk(statement.default_body)

    walk(program.algorithm.body)
    for function in program.functions:
        walk(function.body)
    for procedure in program.procedures:
        walk(procedure.body)
    return found


class DebugSession:
    """Mantiene vivo el generador entre una orden y la siguiente."""

    def __init__(
        self,
        interpreter: object | None,
        diagnostics: tuple[Diagnostic, ...] | list[Diagnostic],
        breakpoints: set[int],
        executable: set[int],
    ) -> None:
        self.interpreter = interpreter
        self.breakpoints = set(breakpoints)
        self.executable = executable
        self.diagnostics = list(diagnostics)
        self.depth = 0
        self.stack: list[Frame] = []
        self.output_parts: list[str] = []
        self.inputs: list[str] = []
        self.status: DebugStatus = "error"
        self.line: int | None = None
        self.column: int | None = None
        self.scope = ""
        self.pending_input: dict[str, str] | None = None
        self.pause_requested = False
        self.stop_requested = False
        self.events: list[dict[str, object]] = []
        self._pending: RuntimeEvent | None = None
        self._generator: Generator[RuntimeEvent, str, None] | None = None
        self._closed = True
        self._resume_mode: StepMode = "continue"
        self._origin_depth = 0
        self._last_input_rejected = False
        self._seq = 0
        self._paused_at: float | None = None
        self.flush: Callable[[], None] | None = None
        if interpreter is None:
            self._record("error")
            return
        scope = getattr(interpreter, "scope_name", "")
        self.scope = scope if isinstance(scope, str) else ""
        self.stack = [{"name": self.scope, "line": None}]
        self._generator = interpreter.run()  # type: ignore[attr-defined]
        self._closed = False
        self._warn_breakpoints()
        self._prime()

    @classmethod
    def failed(cls, diagnostics: tuple[Diagnostic, ...]) -> DebugSession:
        return cls(None, diagnostics, set(), set())

    def command(self, action: str) -> None:
        if action == "stop":
            self._finish_stop()
            return
        if self.status in ("completed", "error", "cancelled", "timeout"):
            raise DebugRejected("Esta ejecución ya terminó.")
        if self.status == "waiting_input":
            raise DebugRejected("Esta ejecución espera un dato.")
        if self.status != "paused":
            raise DebugRejected("Esta ejecución no está en pausa.")
        if action not in ("step", "step_in", "step_out", "continue"):
            raise DebugRejected("La orden no es válida.")
        mode: StepMode = action  # type: ignore[assignment]
        if action != "continue":
            self.pause_requested = False
        self._resume_clock()
        self._resume_mode = mode
        self._origin_depth = self.depth
        self.pending_input = None
        held = self._pull()
        entering = bool(
            held is not None and held.kind == "line" and held.payload.get("call") is True
        )
        if mode == "step_in" and not entering:
            mode = "step"
        event = self._pull() if held is not None and held.kind == "line" else held
        self._walk_from(event, mode, self._origin_depth)

    def provide_input(self, text: str) -> None:
        if self.status != "waiting_input" or self._generator is None:
            raise DebugRejected("Esta ejecución no espera datos.")
        self._resume_clock()
        self._last_input_rejected = False
        try:
            event = self._generator.send(text)
        except StopIteration:
            self.status = "completed"
            self._record("finished")
            self._closed = True
            return
        self._walk_from(event, self._resume_mode, self.depth)
        if not self._last_input_rejected:
            self.inputs.append(text)

    def set_breakpoints(self, lines: set[int]) -> None:
        self.breakpoints = set(lines)
        self.diagnostics = [item for item in self.diagnostics if item.code != "W0504"]
        self._warn_breakpoints()

    def inspect(self, name: str, start: int, count: int) -> dict[str, object]:
        cell = self._cell(name)
        array = None if cell is None else cell.array
        if cell is None or array is None:
            raise DebugRejected(f"{name} no es un arreglo del marco activo.")
        size = max(1, min(count, 40))
        origin = max(0, start)
        chunk = array.cells[origin : origin + size]
        return {
            "name": name,
            "start": origin,
            "total": len(array.cells),
            "lengths": list(array.lengths),
            "base": array.base,
            "values": [format_value(array.type_name, item.value) for item in chunk],
        }

    def close(self) -> None:
        if self._closed or self._generator is None:
            self._closed = True
            return
        self._closed = True
        self._generator.close()

    def snapshot(self) -> dict[str, object]:
        return {
            "status": self.status,
            "line": self.line,
            "column": self.column,
            "scope": self.scope,
            "variables": self.variables(),
            "call_stack": [dict(frame) for frame in self.stack],
            "output": "".join(self.output_parts),
            "diagnostics": tuple(self.diagnostics),
            "pending_input": self.pending_input,
            "last_condition": self._condition(),
            "instruction_count": self._instructions(),
            "breakpoints": sorted(self.breakpoints),
            "event_cursor": self._seq,
        }

    def variables(self) -> dict[str, str]:
        cells = getattr(self.interpreter, "cells", None)
        if not isinstance(cells, dict):
            return {}
        visible: dict[str, str] = {}
        for name, cell in cells.items():
            if not isinstance(name, str):
                continue
            if cell.array is not None:
                count = len(cell.array.cells)
                if count > 24:
                    visible[name] = f"arreglo {list(cell.array.lengths)} · {count} celdas"
                else:
                    visible[name] = format_array(cell.array)
            elif cell.slot_owner is not None and cell.slot_index is not None:
                slot = cell.slot_owner.cells[cell.slot_index]
                visible[name] = format_value(slot.type_name, slot.value)
            elif cell.value is not None:
                visible[name] = format_value(cell.value.type_name, cell.value.value)
        return visible

    def _prime(self) -> None:
        event = self._pull()
        while event is not None and event.kind != "line":
            if self._terminal(event):
                return
            event = self._pull()
        if event is None:
            self.status = "completed"
            self._record("finished")
            return
        self._hold_line(event)

    def _walk_from(self, event: RuntimeEvent | None, mode: StepMode, origin: int) -> None:
        while True:
            if self.stop_requested:
                self._finish_stop()
                return
            if event is None:
                self.status = "completed"
                self._record("finished")
                self.close()
                return
            if self._terminal(event):
                return
            if event.kind == "line" and (
                self.pause_requested or self._should_pause(event, mode, origin)
            ):
                self.pause_requested = False
                self._hold_line(event)
                return
            if event.kind == "output":
                text = event.payload.get("text", "")
                if isinstance(text, str):
                    self.output_parts.append(text)
                self._record("output", text=text if isinstance(text, str) else "")
            elif event.kind == "call":
                self.depth += 1
                name = event.payload.get("name", "")
                self.stack.append(
                    {"name": name if isinstance(name, str) else "", "line": event.line}
                )
                self._record("call", line=event.line, scope=self.scope)
            elif event.kind == "return":
                self.depth = max(0, self.depth - 1)
                if len(self.stack) > 1:
                    self.stack.pop()
                self._record("return", line=event.line)
            elif event.kind == "input_requested":
                name = event.payload.get("name", "")
                type_name = event.payload.get("type", "")
                self.pending_input = {
                    "name": name if isinstance(name, str) else "",
                    "type": type_name if isinstance(type_name, str) else "",
                }
                self.line = event.line
                self.column = event.column
                self.status = "waiting_input"
                self._mark_paused()
                self._record("input_requested")
                return
            elif event.kind == "input_rejected":
                self._last_input_rejected = True
                diagnostic = event.payload.get("diagnostic")
                if isinstance(diagnostic, Diagnostic):
                    self.diagnostics.append(diagnostic)
                self._record("input_rejected")
            elif event.kind == "warning":
                diagnostic = event.payload.get("diagnostic")
                if isinstance(diagnostic, Diagnostic):
                    self.diagnostics.append(diagnostic)
            elif event.kind == "clear":
                self.output_parts.clear()
                self._record("output", text="", output_reset=True)
                self._flush()
            elif event.kind == "delay":
                self._flush()
                raw = event.payload.get("seconds", 0)
                seconds = raw if isinstance(raw, int | float) and not isinstance(raw, bool) else 0
                cancel = getattr(self.interpreter, "cancellation", None)
                pause_for(float(seconds), cancel if isinstance(cancel, Cancellation) else None)
            event = self._pull()

    def _should_pause(self, event: RuntimeEvent, mode: StepMode, origin: int) -> bool:
        if (
            event.line is not None
            and event.line in self.breakpoints
            and event.line in self.executable
        ):
            return True
        if mode == "continue":
            return False
        if mode == "step_out":
            return self.depth < origin
        if mode == "step" and self.depth > origin:
            return False
        return True

    def _hold_line(self, event: RuntimeEvent) -> None:
        self._pending = event
        self.line = event.line
        self.column = event.column
        if isinstance(event.scope, str):
            self.scope = event.scope
        if self.stack:
            self.stack[-1]["line"] = event.line
        self.status = "paused"
        self._mark_paused()
        self._record("paused")

    def _terminal(self, event: RuntimeEvent) -> bool:
        if event.kind == "error":
            diagnostic = event.payload.get("diagnostic")
            if isinstance(diagnostic, Diagnostic):
                self.diagnostics.append(diagnostic)
                self.status = "timeout" if diagnostic.code == "E0411" else "error"
                self.line = diagnostic.span.start_line
                self.column = diagnostic.span.start_col
            else:
                self.status = "error"
            self._record("error")
            self.close()
            return True
        if event.kind == "cancelled":
            diagnostic = event.payload.get("diagnostic")
            if isinstance(diagnostic, Diagnostic):
                self.diagnostics.append(diagnostic)
            self.status = "cancelled"
            self._record("cancelled")
            self.close()
            return True
        if event.kind == "finished":
            self.status = "completed"
            self._record("finished")
            self.close()
            return True
        return False

    def _finish_stop(self) -> None:
        if self.status in ("completed", "error", "cancelled", "timeout"):
            return
        self.stop_requested = True
        interpreter = self.interpreter
        cancel = getattr(interpreter, "cancellation", None)
        if cancel is not None:
            cancel.cancel()
        self.close()
        self.status = "cancelled"
        self.pending_input = None
        if interpreter is not None and not any(item.code == "E0416" for item in self.diagnostics):
            from language_core.ast_nodes import SourceSpan
            from language_core.diagnostics import make_diagnostic

            span = SourceSpan(self.line or 1, self.column or 1, self.line or 1, self.column or 1)
            source = getattr(interpreter, "source", "")
            self.diagnostics.append(
                make_diagnostic(
                    source if isinstance(source, str) else "",
                    "error",
                    "E0416",
                    "La ejecución se canceló.",
                    span,
                    None,
                )
            )
        self._record("cancelled")

    def _warn_breakpoints(self) -> None:
        from language_core.ast_nodes import SourceSpan
        from language_core.diagnostics import make_diagnostic

        source = getattr(self.interpreter, "source", "")
        text = source if isinstance(source, str) else ""
        for number in sorted(self.breakpoints):
            if number in self.executable:
                continue
            span = SourceSpan(number, 1, number, 1)
            self.diagnostics.append(
                make_diagnostic(
                    text,
                    "warning",
                    "W0504",
                    "Esta línea no tiene una sentencia ejecutable. El punto de interrupción no detiene.",
                    span,
                    "Márcalo en una sentencia, por ejemplo una asignación o un Escribir.",
                )
            )

    def _pull(self) -> RuntimeEvent | None:
        if self._pending is not None:
            event = self._pending
            self._pending = None
            return event
        if self._closed or self._generator is None:
            return None
        try:
            return next(self._generator)
        except StopIteration:
            return None

    def _record(self, kind: str, **payload: object) -> None:
        self._seq += 1
        self.events.append(
            {
                "id": self._seq,
                "event": kind,
                "status": self.status,
                "line": self.line,
                "column": self.column,
                "scope": self.scope,
                "output": "".join(self.output_parts),
                "variables": self.variables(),
                "call_stack": [dict(frame) for frame in self.stack],
                "last_condition": self._condition(),
                "pending_input": self.pending_input,
                **payload,
            }
        )

    def _flush(self) -> None:
        if self.flush is not None:
            self.flush()

    def _mark_paused(self) -> None:
        clock = getattr(self.interpreter, "clock", None)
        if callable(clock):
            mark = clock()
            if isinstance(mark, int | float):
                self._paused_at = float(mark)

    def _resume_clock(self) -> None:
        interpreter = self.interpreter
        if interpreter is None or self._paused_at is None:
            return
        clock = getattr(interpreter, "clock", None)
        started = getattr(interpreter, "started", None)
        if not callable(clock) or isinstance(started, bool) or not isinstance(started, int | float):
            return
        mark = clock()
        if isinstance(mark, bool) or not isinstance(mark, int | float):
            return
        running: Any = interpreter
        running.started = float(started) + (float(mark) - self._paused_at)
        self._paused_at = None

    def _condition(self) -> str | None:
        value = getattr(self.interpreter, "last_condition", None)
        return value if isinstance(value, str) else None

    def _instructions(self) -> int:
        count = getattr(self.interpreter, "instruction_count", 0)
        return count if isinstance(count, int) else 0

    def _cell(self, name: str) -> Cell | None:
        cells = getattr(self.interpreter, "cells", None)
        if not isinstance(cells, dict):
            return None
        cell = cells.get(name)
        return cell if isinstance(cell, Cell) else None


def open_debug(
    source: str,
    profile: object | None = None,
    breakpoints: set[int] | None = None,
    *,
    limits: object | None = None,
    cancellation: object | None = None,
    clock: object | None = None,
    rng: object | None = None,
) -> DebugSession:
    """Compila y deja la sesión pausada en la primera sentencia."""
    import random
    import time

    from language_core.grammar import STRICT
    from language_core.interpreter import Interpreter, compile_source
    from language_core.runtime import Cancellation, Limits

    chosen = profile or STRICT
    compiled = compile_source(source, chosen)  # type: ignore[arg-type]
    errors = [item for item in compiled.diagnostics if item.severity == "error"]
    if compiled.program is None or errors:
        return DebugSession.failed(compiled.diagnostics)
    active_limits = limits if isinstance(limits, Limits) else Limits.from_profile(chosen)  # type: ignore[arg-type]
    active_cancel = cancellation if isinstance(cancellation, Cancellation) else Cancellation()
    active_clock = clock if callable(clock) else time.monotonic
    active_rng = rng if isinstance(rng, random.Random) else random.Random()
    interpreter = Interpreter(
        compiled.program,
        source,
        chosen,  # type: ignore[arg-type]
        active_limits,
        active_cancel,
        active_clock,
        active_rng,
    )
    return DebugSession(
        interpreter,
        compiled.diagnostics,
        set(breakpoints or ()),
        executable_lines(compiled.program),
    )


def open_program(
    program: object,
    source: str,
    diagnostics: tuple[Diagnostic, ...] | list[Diagnostic],
    *,
    limits: object | None = None,
    cancellation: object | None = None,
    clock: object | None = None,
    rng: object | None = None,
) -> DebugSession:
    """Pausa en la primera sentencia del árbol. No vuelve a leer el texto."""
    import random
    import time

    from language_core.ast_nodes import Program
    from language_core.grammar import STRICT
    from language_core.interpreter import Interpreter
    from language_core.runtime import Cancellation, Limits

    notes = tuple(diagnostics)
    errors = [item for item in notes if item.severity == "error"]
    if not isinstance(program, Program) or errors:
        return DebugSession.failed(notes)
    active_limits = limits if isinstance(limits, Limits) else Limits.from_profile(STRICT)
    active_cancel = cancellation if isinstance(cancellation, Cancellation) else Cancellation()
    active_clock = clock if callable(clock) else time.monotonic
    active_rng = rng if isinstance(rng, random.Random) else random.Random()
    interpreter = Interpreter(
        program,
        source,
        STRICT,
        active_limits,
        active_cancel,
        active_clock,
        active_rng,
    )
    return DebugSession(interpreter, notes, set(), executable_lines(program))


def _first(generator: Generator[RuntimeEvent, str, None]) -> RuntimeEvent | None:
    try:
        return next(generator)
    except StopIteration:
        return None


def _next(generator: Generator[RuntimeEvent, str, None]) -> RuntimeEvent | None:
    try:
        return next(generator)
    except StopIteration:
        return None


def _send(generator: Generator[RuntimeEvent, str, None], text: str) -> RuntimeEvent | None:
    try:
        return generator.send(text)
    except StopIteration:
        return None
