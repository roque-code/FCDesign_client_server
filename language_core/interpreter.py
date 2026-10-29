"""Intérprete del AST.

Recorre el árbol y produce eventos. No usa eval ni exec.
Definir crea la celda para todo el algoritmo, aunque esté escrita dentro de un Si.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Generator
from decimal import Decimal, DivisionByZero, InvalidOperation, Overflow, localcontext
from typing import Literal, NoReturn

from language_core.ast_nodes import (
    AssignStmt,
    BinaryExpr,
    CallExpr,
    CallStmt,
    ClearStmt,
    DefineStmt,
    DimensionStmt,
    Expr,
    ForStmt,
    IfStmt,
    IndexExpr,
    LiteralExpr,
    NameExpr,
    Param,
    Program,
    ReadStmt,
    RepeatStmt,
    SourceSpan,
    Stmt,
    SwitchStmt,
    TypeName,
    UnaryExpr,
    WaitStmt,
    WhileStmt,
    WriteStmt,
)
from language_core.debugger import drive
from language_core.diagnostics import Diagnostic, make_diagnostic
from language_core.errors import Cancelled, ExecFault
from language_core.grammar import STRICT, LanguageProfile
from language_core.lexer import lex
from language_core.parser import parse
from language_core.runtime import (
    ArrayValue,
    Cancellation,
    Cell,
    CompileResult,
    ExecutionResult,
    Limits,
    RuntimeEvent,
    Value,
    format_array,
)
from language_core.semantic_analyzer import analyze
from language_core.stdlib import StdFault, call_stdlib, std_arity
from language_core.type_system import format_value, parse_input

_MAX_BITS = 20_000
_MAX_WAIT_SECONDS = 60
_MAX_EXPONENT = 10_000
Clock = Callable[[], float]
Stepper = Generator[RuntimeEvent, str, None]
ValueStep = Generator[RuntimeEvent, str, Value]
BindStep = Generator[RuntimeEvent, str, dict[str, Cell]]
CellStep = Generator[RuntimeEvent, str, Cell]
IndexStep = Generator[RuntimeEvent, str, int]


def compile_source(source: str, profile: LanguageProfile | None = None) -> CompileResult:
    """Valida el fuente sin ejecutarlo."""
    chosen = profile or STRICT
    lexed = lex(source)
    program, syntax = parse(lexed.tokens, source, chosen)
    diagnostics = list(lexed.diagnostics)
    diagnostics.extend(syntax)
    if program is not None:
        diagnostics.extend(analyze(program, chosen, source))
    return CompileResult(program, tuple(diagnostics))


def execute_source(
    source: str,
    inputs: list[str] | None = None,
    profile: LanguageProfile | None = None,
    *,
    limits: Limits | None = None,
    cancellation: Cancellation | None = None,
    clock: Clock | None = None,
    rng: random.Random | None = None,
) -> ExecutionResult:
    """Compila y, si no hay errores, ejecuta el algoritmo."""
    chosen = profile or STRICT
    compiled = compile_source(source, chosen)
    errors = [item for item in compiled.diagnostics if item.severity == "error"]
    if compiled.program is None or errors:
        return ExecutionResult("error", "", compiled.diagnostics, {})
    interpreter = Interpreter(
        compiled.program,
        source,
        chosen,
        limits or Limits.from_profile(chosen),
        cancellation or Cancellation(),
        clock or time.monotonic,
        rng or random.Random(),
    )
    return drive(interpreter.run(), list(inputs or []), compiled.diagnostics, interpreter.cells)


class Interpreter:
    """Sesión de ejecución de un programa ya aceptado por el analizador."""

    def __init__(
        self,
        program: Program,
        source: str,
        profile: LanguageProfile,
        limits: Limits,
        cancellation: Cancellation,
        clock: Clock,
        rng: random.Random,
    ) -> None:
        self.program = program
        self.source = source
        self.profile = profile
        self.limits = limits
        self.cancellation = cancellation
        self.clock = clock
        self.rng = rng
        self.scope_name = program.algorithm.name
        self.cells: dict[str, Cell] = {}
        self.loop_spans: list[SourceSpan] = []
        self.instruction_count = 0
        self.output_chars = 0
        self.allocated_cells = 0
        self.call_depth = 0
        self.started = clock()
        self.last_condition: str | None = None

    def run(self) -> Stepper:
        try:
            self._collect(self.program.algorithm.body)
            yield from self._block(self.program.algorithm.body)
            yield RuntimeEvent(kind="finished", scope=self.scope_name)
        except ExecFault as exc:
            diagnostic = exc.diagnostic
            yield RuntimeEvent(
                kind="error",
                line=diagnostic.span.start_line,
                column=diagnostic.span.start_col,
                scope=self.scope_name,
                payload={"diagnostic": diagnostic},
            )
        except Cancelled:
            span = self.program.algorithm.span
            diagnostic = self._diagnostic(
                "error",
                "E0416",
                "La ejecución se canceló.",
                span,
                None,
            )
            yield RuntimeEvent(
                kind="cancelled", scope=self.scope_name, payload={"diagnostic": diagnostic}
            )

    def _collect(self, statements: tuple[Stmt, ...]) -> None:
        for statement in statements:
            if isinstance(statement, DefineStmt):
                for name in statement.names:
                    self.cells.setdefault(name, Cell(statement.type_name))
            elif isinstance(statement, IfStmt):
                self._collect(statement.then_body)
                if statement.else_body is not None:
                    self._collect(statement.else_body)
            elif isinstance(statement, (WhileStmt, RepeatStmt, ForStmt)):
                self._collect(statement.body)
            elif isinstance(statement, SwitchStmt):
                for case in statement.cases:
                    self._collect(case.body)
                if statement.default_body is not None:
                    self._collect(statement.default_body)

    def _block(self, statements: tuple[Stmt, ...]) -> Stepper:
        for statement in statements:
            yield from self._statement(statement)

    def _statement(self, statement: Stmt) -> Stepper:
        self._charge(statement.span)
        yield self._line(statement.span, call=isinstance(statement, CallStmt))
        if isinstance(statement, DefineStmt):
            return
        if isinstance(statement, AssignStmt):
            yield from self._assign(statement)
            return
        if isinstance(statement, ReadStmt):
            yield from self._read(statement)
            return
        if isinstance(statement, WriteStmt):
            yield from self._write(statement)
            return
        if isinstance(statement, ClearStmt):
            yield from self._clear(statement)
            return
        if isinstance(statement, WaitStmt):
            yield from self._wait(statement)
            return
        if isinstance(statement, IfStmt):
            yield from self._if(statement)
            return
        if isinstance(statement, WhileStmt):
            yield from self._while(statement)
            return
        if isinstance(statement, RepeatStmt):
            yield from self._repeat(statement)
            return
        if isinstance(statement, ForStmt):
            yield from self._for(statement)
            return
        if isinstance(statement, DimensionStmt):
            yield from self._dimension(statement)
            return
        if isinstance(statement, SwitchStmt):
            yield from self._switch(statement)
            return
        yield from self._invoke(statement.call, as_statement=True)

    def _assign(self, statement: AssignStmt) -> Stepper:
        if statement.target.indexes:
            array_cell = self._array_cell(statement.target.name, statement.span)
            if array_cell.array is None:
                self._fail(
                    "E0303", f"{statement.target.name} no es un arreglo.", statement.span, None
                )
            offset = yield from self._offset(
                array_cell.array, statement.target.indexes, statement.span
            )
            value = yield from self._eval(statement.value)
            array_cell.array.cells[offset] = self._coerce(
                array_cell.type_name, value, statement.span
            )
            return
        value = yield from self._eval(statement.value)
        self._store(statement.target.name, value, statement.span)

    def _read(self, statement: ReadStmt) -> Stepper:
        for target in statement.targets:
            slot: tuple[ArrayValue, int] | None = None
            if target.indexes:
                array_cell = self._array_cell(target.name, target.span)
                if array_cell.array is None:
                    self._fail("E0303", f"{target.name} no es un arreglo.", target.span, None)
                offset = yield from self._offset(array_cell.array, target.indexes, target.span)
                slot = (array_cell.array, offset)
                type_name = array_cell.type_name
            else:
                cell = self.cells.get(target.name)
                if cell is None and not self.profile.require_declarations:
                    cell = Cell("cadena")
                    self.cells[target.name] = cell
                if cell is None:
                    self._fail(
                        "E0301",
                        f"La variable {target.name} no está declarada.",
                        target.span,
                        f"Agrégala con Definir {target.name} Como Entero;",
                    )
                if cell.array is not None:
                    self._fail(
                        "E0303",
                        f"Al arreglo {target.name} le falta el índice.",
                        target.span,
                        f"Escribe Leer {target.name}[1];",
                    )
                type_name = cell.type_name
            while True:
                entered = yield RuntimeEvent(
                    kind="input_requested",
                    line=target.span.start_line,
                    column=target.span.start_col,
                    scope=self.scope_name,
                    payload={"name": target.name, "type": type_name},
                )
                text = entered if isinstance(entered, str) else ""
                parsed = parse_input(type_name, text)
                if parsed is None:
                    diagnostic = self._diagnostic(
                        "error",
                        "E0406",
                        f"El valor {text!r} no es compatible con {type_name}.",
                        target.span,
                        _input_suggestion(type_name),
                    )
                    yield RuntimeEvent(
                        kind="input_rejected",
                        line=target.span.start_line,
                        column=target.span.start_col,
                        scope=self.scope_name,
                        payload={"diagnostic": diagnostic},
                    )
                    continue
                if slot is None:
                    self._store(target.name, Value(type_name, parsed), target.span)
                else:
                    array, offset = slot
                    array.cells[offset] = self._coerce(
                        type_name, Value(type_name, parsed), target.span
                    )
                yield from self._emit_text(f"{text}\n", target.span)
                break

    def _write(self, statement: WriteStmt) -> Stepper:
        parts: list[str] = []
        for expr in statement.values:
            value = yield from self._eval(expr)
            parts.append(format_value(value.type_name, value.value))
        text = "".join(parts)
        if statement.newline:
            text += "\n"
        yield from self._emit_text(text, statement.span)

    def _clear(self, statement: ClearStmt) -> Stepper:
        self.output_chars = 0
        yield RuntimeEvent(
            kind="clear",
            line=statement.span.start_line,
            column=statement.span.start_col,
            scope=self.scope_name,
        )

    def _wait(self, statement: WaitStmt) -> Stepper:
        value = yield from self._eval(statement.seconds)
        seconds = self._wait_seconds(value, statement.seconds.span)
        started = self.clock()
        yield RuntimeEvent(
            kind="delay",
            line=statement.span.start_line,
            column=statement.span.start_col,
            scope=self.scope_name,
            payload={"seconds": seconds},
        )
        elapsed = self.clock() - started
        if isinstance(elapsed, int | float) and not isinstance(elapsed, bool) and elapsed > 0:
            self.started += elapsed

    def _wait_seconds(self, value: Value, span: SourceSpan) -> float:
        if value.type_name == "entero" and isinstance(value.value, int):
            number = float(value.value)
        elif value.type_name == "real" and isinstance(value.value, Decimal):
            number = float(value.value)
        else:
            self._fail(
                "E0303",
                "La espera debe ser un número.",
                span,
                "Usa un Entero o un Real.",
            )
        if number < 0 or number > _MAX_WAIT_SECONDS:
            self._fail(
                "E0417",
                f"La espera debe estar entre 0 y {_MAX_WAIT_SECONDS} segundos.",
                span,
                "Usa un tiempo más corto.",
            )
        return number

    def _emit_text(self, text: str, span: SourceSpan) -> Stepper:
        if self.output_chars + len(text) > self.limits.max_output_chars:
            self._fail(
                "E0414",
                "La salida es demasiado larga.",
                span,
                "Reduce lo que se escribe dentro del ciclo.",
            )
        self.output_chars += len(text)
        yield RuntimeEvent(
            kind="output",
            line=span.start_line,
            column=span.start_col,
            scope=self.scope_name,
            payload={"text": text},
        )

    def _if(self, statement: IfStmt) -> Stepper:
        condition = yield from self._eval(statement.condition)
        self._expect_logic(condition, statement.condition.span)
        self.last_condition = "Verdadero" if condition.value is True else "Falso"
        if condition.value is True:
            yield from self._block(statement.then_body)
        elif statement.else_body is not None:
            yield from self._block(statement.else_body)

    def _while(self, statement: WhileStmt) -> Stepper:
        self.loop_spans.append(statement.span)
        try:
            first = True
            while True:
                if not first:
                    self._charge(statement.span)
                    yield self._line(statement.span)
                first = False
                condition = yield from self._eval(statement.condition)
                self._expect_logic(condition, statement.condition.span)
                self.last_condition = "Verdadero" if condition.value is True else "Falso"
                if condition.value is False:
                    break
                yield from self._block(statement.body)
        finally:
            self.loop_spans.pop()

    def _repeat(self, statement: RepeatStmt) -> Stepper:
        self.loop_spans.append(statement.span)
        try:
            first = True
            while True:
                if not first:
                    self._charge(statement.span)
                    yield self._line(statement.span)
                first = False
                yield from self._block(statement.body)
                condition = yield from self._eval(statement.condition)
                self._expect_logic(condition, statement.condition.span)
                self.last_condition = "Verdadero" if condition.value is True else "Falso"
                if condition.value is True:
                    break
        finally:
            self.loop_spans.pop()

    def _for(self, statement: ForStmt) -> Stepper:
        start = self._require_int(
            (yield from self._eval(statement.start)),
            statement.start.span,
            "El inicio del Para debe ser Entero.",
        )
        end = self._require_int(
            (yield from self._eval(statement.end)),
            statement.end.span,
            "El límite del Para debe ser Entero.",
        )
        if statement.step is None:
            step = 1 if start <= end else -1
        else:
            step = self._require_int(
                (yield from self._eval(statement.step)),
                statement.step.span,
                "El paso del Para debe ser Entero.",
            )
            if step == 0:
                self._fail(
                    "E0405",
                    "El paso del Para no puede ser cero.",
                    statement.step.span,
                    "Usa 1, -1 u otro entero distinto de cero.",
                )
        self._store(statement.variable, Value("entero", start), statement.variable_span)
        if not _enters(start, end, step) and self.profile.beginner_warnings:
            diagnostic = self._diagnostic(
                "warning",
                "W0502",
                "Este Para no ejecuta el cuerpo: el paso se aleja del límite.",
                statement.span,
                "Revisa el inicio, el Hasta y el Paso.",
            )
            yield RuntimeEvent(
                kind="warning", scope=self.scope_name, payload={"diagnostic": diagnostic}
            )
        self.loop_spans.append(statement.span)
        try:
            current = start
            first = True
            while _enters(current, end, step):
                if not first:
                    self._charge(statement.span)
                    yield self._line(statement.span)
                first = False
                yield from self._block(statement.body)
                current_value = self._read_cell(statement.variable, statement.variable_span)
                current = self._require_int(
                    current_value,
                    statement.variable_span,
                    "La variable del Para debe seguir siendo Entero.",
                )
                current += step
                self._check_int_size(current, statement.span)
                self._store(statement.variable, Value("entero", current), statement.variable_span)
        finally:
            self.loop_spans.pop()

    def _eval(self, expr: Expr) -> ValueStep:
        if isinstance(expr, LiteralExpr):
            if expr.kind in ("cadena", "caracter") and isinstance(expr.value, str):
                self._check_text(expr.value, expr.span)
            return Value(expr.kind, expr.value)
        if isinstance(expr, NameExpr):
            return self._read_cell(expr.name, expr.span)
        if isinstance(expr, UnaryExpr):
            return self._unary(expr, (yield from self._eval(expr.operand)))
        if isinstance(expr, BinaryExpr):
            if expr.operator in ("and", "or"):
                return (yield from self._logic(expr))
            right_wait = self._eval(expr.right)
            left = yield from self._eval(expr.left)
            right = yield from right_wait
            return self._binary(expr, left, right)
        if isinstance(expr, IndexExpr):
            return (yield from self._load_index(expr))
        if isinstance(expr, CallExpr):
            produced = yield from self._invoke(expr, as_statement=False)
            if produced is None:
                self._fail(
                    "E0312",
                    f"{expr.name} es un procedimiento y no devuelve un valor.",
                    expr.span,
                    "Úsalo como sentencia.",
                )
            return produced
        self._fail(
            "E0201",
            "No se puede evaluar esta expresión.",
            getattr(expr, "span", self.program.span),
            None,
        )

    def _logic(self, expr: BinaryExpr) -> ValueStep:
        left = yield from self._eval(expr.left)
        self._expect_logic(left, expr.left.span)
        if expr.operator == "and" and left.value is False:
            return Value("logico", False)
        if expr.operator == "or" and left.value is True:
            return Value("logico", True)
        right = yield from self._eval(expr.right)
        self._expect_logic(right, expr.right.span)
        return Value("logico", right.value is True)

    def _unary(self, expr: UnaryExpr, operand: Value) -> Value:
        if expr.operator == "not":
            self._expect_logic(operand, expr.operand.span)
            return Value("logico", operand.value is False)
        if operand.type_name == "entero" and isinstance(operand.value, int):
            signed = operand.value if expr.operator == "pos" else -operand.value
            self._check_int_size(signed, expr.span)
            return Value("entero", signed)
        if operand.type_name == "real" and isinstance(operand.value, Decimal):
            signed_real = operand.value if expr.operator == "pos" else -operand.value
            return Value("real", signed_real)
        self._fail(
            "E0305", "El signo solo se aplica a números.", expr.span, "Usa un Entero o un Real."
        )

    def _binary(self, expr: BinaryExpr, left: Value, right: Value) -> Value:
        operator = expr.operator
        if operator in ("add", "sub", "mul"):
            return self._arithmetic(operator, left, right, expr.span)
        if operator == "div":
            return Value("real", self._divide(left, right, expr.span))
        if operator == "idiv":
            return Value("entero", self._idiv(left, right, expr.span))
        if operator == "mod":
            return Value("entero", self._mod(left, right, expr.span))
        if operator == "pow":
            return self._power(left, right, expr.span)
        if operator in ("eq", "neq", "lt", "lte", "gt", "gte"):
            return Value("logico", self._compare(operator, left, right, expr.span))
        self._fail("E0305", "Esta operación no está permitida.", expr.span, None)

    def _arithmetic(self, operator: str, left: Value, right: Value, span: SourceSpan) -> Value:
        if left.type_name == "entero" and right.type_name == "entero":
            if not isinstance(left.value, int) or not isinstance(right.value, int):
                self._fail("E0305", "Esta operación solo acepta números.", span, None)
            result = _int_op(operator, left.value, right.value)
            self._check_int_size(result, span)
            return Value("entero", result)
        if left.type_name in ("entero", "real") and right.type_name in ("entero", "real"):
            return Value("real", _decimal_op(operator, _as_decimal(left), _as_decimal(right)))
        self._fail(
            "E0305",
            "El operador no acepta estos tipos.",
            span,
            "En el perfil estricto + es numérico. Para texto usaremos Concatenar.",
        )

    def _divide(self, left: Value, right: Value, span: SourceSpan) -> Decimal:
        denominator = _as_decimal(right)
        if denominator == 0:
            self._fail(
                "E0402",
                "No se puede dividir entre cero.",
                span,
                "Revisa el divisor antes de usar /.",
            )
        try:
            with localcontext() as ctx:
                ctx.prec = 28
                return _as_decimal(left) / denominator
        except (DivisionByZero, InvalidOperation, Overflow):
            self._fail(
                "E0402",
                "No se puede dividir entre cero.",
                span,
                "Revisa el divisor antes de usar /.",
            )

    def _idiv(self, left: Value, right: Value, span: SourceSpan) -> int:
        numerator, divisor = self._int_pair(left, right, span, "DIV")
        if divisor == 0:
            self._fail(
                "E0402", "No se puede dividir entre cero.", span, "Revisa el divisor de DIV."
            )
        return int(Decimal(numerator) / Decimal(divisor))

    def _mod(self, left: Value, right: Value, span: SourceSpan) -> int:
        numerator, divisor = self._int_pair(left, right, span, "MOD")
        if divisor == 0:
            self._fail(
                "E0402",
                "No se puede calcular el residuo de una división entre cero.",
                span,
                "Revisa el divisor de MOD.",
            )
        quotient = int(Decimal(numerator) / Decimal(divisor))
        return numerator - quotient * divisor

    def _power(self, left: Value, right: Value, span: SourceSpan) -> Value:
        if left.type_name == "entero" and right.type_name == "entero":
            if not isinstance(left.value, int) or not isinstance(right.value, int):
                self._fail("E0403", "La potencia no es válida.", span, None)
            if left.value == 0 and right.value == 0:
                self._fail(
                    "E0403",
                    "0 elevado a 0 no está definido.",
                    span,
                    "Cambia la base o el exponente.",
                )
            if right.value < 0:
                return Value(
                    "real", self._decimal_power(Decimal(left.value), Decimal(right.value), span)
                )
            if right.value > _MAX_EXPONENT or (
                left.value not in (-1, 0, 1) and left.value.bit_length() * right.value > _MAX_BITS
            ):
                self._fail(
                    "E0413",
                    "La potencia produce un número demasiado grande.",
                    span,
                    "Usa un exponente más pequeño.",
                )
            return Value("entero", left.value**right.value)
        base = _as_decimal(left)
        exponent = _as_decimal(right)
        if base == 0 and exponent == 0:
            self._fail(
                "E0403", "0 elevado a 0 no está definido.", span, "Cambia la base o el exponente."
            )
        if base < 0 and exponent != exponent.to_integral_value():
            self._fail(
                "E0403",
                "No se puede elevar un negativo a un real no entero.",
                span,
                "Usa un exponente entero o una base positiva.",
            )
        return Value("real", self._decimal_power(base, exponent, span))

    def _decimal_power(self, base: Decimal, exponent: Decimal, span: SourceSpan) -> Decimal:
        try:
            with localcontext() as ctx:
                ctx.prec = 28
                return base**exponent
        except (InvalidOperation, Overflow, DivisionByZero):
            self._fail(
                "E0403", "La potencia no se puede calcular.", span, "Revisa la base y el exponente."
            )

    def _compare(self, operator: str, left: Value, right: Value, span: SourceSpan) -> bool:
        if left.type_name in ("entero", "real") and right.type_name in ("entero", "real"):
            return _ordered(operator, _as_decimal(left), _as_decimal(right))
        if left.type_name == right.type_name and left.type_name in ("cadena", "caracter", "logico"):
            if left.type_name == "logico" and operator not in ("eq", "neq"):
                self._fail(
                    "E0306", "Un lógico solo se compara con == o <>.", span, "Usa Verdadero y Falso."
                )
            return _ordered(operator, left.value, right.value)
        self._fail("E0306", "Estos valores no se pueden comparar entre sí.", span, None)

    def _store(self, name: str, value: Value, span: SourceSpan) -> None:
        cell = self.cells.get(name)
        if cell is None:
            if not self.profile.require_declarations:
                cell = Cell(value.type_name)
                self.cells[name] = cell
            else:
                self._fail(
                    "E0301",
                    f"La variable {name} no está declarada.",
                    span,
                    f"Agrégala con Definir {name} Como Entero;",
                )
        if cell.slot_owner is not None and cell.slot_index is not None:
            cell.slot_owner.cells[cell.slot_index] = self._coerce(cell.type_name, value, span)
            return
        if cell.array is not None:
            self._fail(
                "E0303",
                f"Al arreglo {name} le falta el índice.",
                span,
                f"Escribe {name}[1] <- ...;",
            )
        stored = self._coerce(cell.type_name, value, span)
        cell.value = stored

    def _read_cell(self, name: str, span: SourceSpan) -> Value:
        cell = self.cells.get(name)
        if cell is None:
            self._fail(
                "E0301",
                f"La variable {name} no está declarada.",
                span,
                f"Agrégala con Definir {name} Como Entero;",
            )
        if cell.slot_owner is not None and cell.slot_index is not None:
            return cell.slot_owner.cells[cell.slot_index]
        if cell.array is not None:
            self._fail(
                "E0303",
                f"Al arreglo {name} le falta el índice.",
                span,
                f"Escribe {name}[1].",
            )
        if cell.value is None:
            self._fail(
                "E0401",
                f"La variable {name} todavía no tiene valor.",
                span,
                f"Asígnala antes de usarla, por ejemplo {name} <- 0;",
            )
        return cell.value

    def _coerce(self, target: str, value: Value, span: SourceSpan) -> Value:
        if target == value.type_name:
            if target == "caracter" and (not isinstance(value.value, str) or len(value.value) != 1):
                self._fail(
                    "E0303", "Un Carácter admite exactamente un símbolo.", span, "Usa una Cadena."
                )
            return value
        if target == "real" and value.type_name == "entero" and isinstance(value.value, int):
            if not self.profile.implicit_widening:
                self._fail(
                    "E0303", "No se puede asignar un Entero a un Real en este perfil.", span, None
                )
            return Value("real", Decimal(value.value))
        if target == "caracter" and value.type_name == "cadena" and isinstance(value.value, str):
            if len(value.value) != 1:
                self._fail(
                    "E0303",
                    "No se puede asignar esta cadena a un Carácter.",
                    span,
                    "La cadena debe tener un solo símbolo.",
                )
            return Value("caracter", value.value)
        if target == "cadena" and value.type_name == "caracter":
            return Value("cadena", value.value)
        self._fail(
            "E0303",
            "El valor no corresponde al tipo de la variable.",
            span,
            "Revisa el Definir y la expresión.",
        )

    def _expect_logic(self, value: Value, span: SourceSpan) -> None:
        if value.type_name != "logico":
            self._fail(
                "E0304",
                "La condición debe ser un valor lógico.",
                span,
                "Compara con ==, < o >, o usa Verdadero y Falso.",
            )

    def _require_int(self, value: Value, span: SourceSpan, message: str) -> int:
        if value.type_name != "entero" or not isinstance(value.value, int):
            self._fail("E0303", message, span, "Usa un número sin decimales.")
        return value.value

    def _int_pair(
        self, left: Value, right: Value, span: SourceSpan, symbol: str
    ) -> tuple[int, int]:
        if (
            left.type_name != "entero"
            or right.type_name != "entero"
            or not isinstance(left.value, int)
            or not isinstance(right.value, int)
        ):
            self._fail(
                "E0305",
                f"{symbol} solo acepta números enteros.",
                span,
                "Si necesitas decimales, usa /.",
            )
        return left.value, right.value

    def _check_int_size(self, value: int, span: SourceSpan) -> None:
        if value.bit_length() > _MAX_BITS:
            self._fail("E0413", "El número supera el tamaño permitido.", span, "Reduce el cálculo.")

    def _check_text(self, text: str, span: SourceSpan) -> None:
        if len(text) > self.limits.max_string_length:
            self._fail(
                "E0413", "El texto supera el tamaño permitido.", span, "Usa un texto más corto."
            )

    def _charge(self, span: SourceSpan) -> None:
        if self.cancellation.requested:
            raise Cancelled
        self.instruction_count += 1
        if self.instruction_count > self.limits.max_instructions:
            origin = self.loop_spans[-1] if self.loop_spans else span
            self._fail(
                "E0410",
                "Se alcanzó el límite de instrucciones. Si estás en un ciclo, la condición podría no volverse falsa.",
                origin,
                "Revisa el Mientras, el Repetir o el Paso del Para.",
            )
        elapsed_ms = (self.clock() - self.started) * 1000
        if elapsed_ms > self.limits.max_time_ms:
            self._fail(
                "E0411",
                "Se agotó el tiempo de ejecución.",
                span,
                "Revisa si hay un ciclo que no termina.",
            )

    def _line(self, span: SourceSpan, *, call: bool = False) -> RuntimeEvent:
        return RuntimeEvent(
            kind="line",
            line=span.start_line,
            column=span.start_col,
            scope=self.scope_name,
            payload={"variables": self._snapshot(), "call": call},
        )

    def _dimension(self, statement: DimensionStmt) -> Stepper:
        for decl in statement.declarations:
            lengths: list[int] = []
            for expr in decl.lengths:
                length = self._require_int(
                    (yield from self._eval(expr)),
                    expr.span,
                    "El tamaño de una dimensión debe ser Entero.",
                )
                if length < 1:
                    self._fail(
                        "E0303",
                        "El tamaño de una dimensión debe ser mayor que cero.",
                        expr.span,
                        "Usa un entero positivo, por ejemplo 10.",
                    )
                lengths.append(length)
            if len(lengths) > 4:
                self._fail(
                    "E0313",
                    "Un arreglo admite como máximo 4 dimensiones.",
                    decl.span,
                    "Divide el dato en arreglos más chicos.",
                )
            existing = self.cells.get(decl.name)
            declared = tuple(lengths)
            if existing is not None and existing.array is not None:
                if existing.array.lengths != declared:
                    self._fail(
                        "E0404",
                        f"El arreglo {decl.name} mide {existing.array.lengths} y aquí se declaró {declared}.",
                        decl.span,
                        "Usa el mismo tamaño que el arreglo recibido.",
                    )
                continue
            total = 1
            for length in lengths:
                total *= length
            if self.allocated_cells + total > self.limits.max_array_cells:
                self._fail(
                    "E0413",
                    "El arreglo supera el número de celdas permitido.",
                    decl.span,
                    "Reduce el tamaño o la cantidad de arreglos.",
                )
            element = decl.type_name
            if element is None and existing is not None:
                element = existing.type_name
            if element is None:
                element = "entero"
            array = ArrayValue(
                element,
                declared,
                self.profile.index_base,
                [_default_value(element) for _ in range(total)],
            )
            self.allocated_cells += total
            self.cells[decl.name] = Cell(element, array=array, dimensions=len(declared))

    def _switch(self, statement: SwitchStmt) -> Stepper:
        selector = yield from self._eval(statement.selector)
        for case in statement.cases:
            for label in case.labels:
                candidate = yield from self._eval(label)
                if self._compare("eq", selector, candidate, label.span):
                    yield from self._block(case.body)
                    return
        if statement.default_body is not None:
            yield from self._block(statement.default_body)

    def _invoke(self, call: CallExpr, *, as_statement: bool) -> ValueStep:
        if std_arity(call.name) is not None:
            arguments: list[Value] = []
            for arg in call.args:
                arguments.append((yield from self._eval(arg)))
            try:
                return call_stdlib(
                    call.name,
                    arguments,
                    rng=self.rng,
                    index_base=self.profile.index_base,
                )
            except StdFault as exc:
                self._fail(exc.code, exc.message, call.span, exc.suggestion)
        function = next((item for item in self.program.functions if item.name == call.name), None)
        procedure = next((item for item in self.program.procedures if item.name == call.name), None)
        if function is None and procedure is None:
            self._fail(
                "E0310",
                f"No existe la función o el procedimiento {call.name}.",
                call.span,
                "Revisa el nombre.",
            )
        if procedure is not None and not as_statement:
            self._fail(
                "E0312",
                f"{call.name} es un procedimiento y no devuelve un valor.",
                call.span,
                "Úsalo como sentencia.",
            )
        routine_params = function.params if function is not None else procedure.params  # type: ignore[union-attr]
        body = function.body if function is not None else procedure.body  # type: ignore[union-attr]
        result_name = function.result_name if function is not None else None
        if len(call.args) != len(routine_params):
            self._fail(
                "E0311",
                f"{call.name} espera {len(routine_params)} argumentos y recibió {len(call.args)}.",
                call.span,
                "Revisa la lista entre paréntesis.",
            )
        previous_cells = self.cells
        previous_scope = self.scope_name
        previous_allocated = self.allocated_cells
        entered = False
        try:
            bound = yield from self._bind(routine_params, call.args, body)
            self.call_depth += 1
            entered = True
            if self.call_depth > self.limits.max_call_depth:
                self._fail(
                    "E0412",
                    "Se alcanzó la profundidad máxima de llamadas.",
                    call.span,
                    "Revisa si la recursión se acerca al caso base.",
                )
            self.cells = bound
            self.scope_name = call.name
            self._collect(body)
            yield RuntimeEvent(
                kind="call",
                line=call.span.start_line,
                column=call.span.start_col,
                scope=call.name,
                payload={"name": call.name},
            )
            yield from self._block(body)
            if result_name is None:
                produced = Value("entero", 0)
            else:
                produced = self._read_cell(result_name, call.span)
            yield RuntimeEvent(
                kind="return",
                line=call.span.start_line,
                column=call.span.start_col,
                scope=previous_scope,
                payload={"name": call.name},
            )
            return produced
        finally:
            self.allocated_cells = previous_allocated
            if entered:
                self.cells = previous_cells
                self.scope_name = previous_scope
                self.call_depth -= 1

    def _bind(
        self, params: tuple[Param, ...], args: tuple[Expr, ...], body: tuple[Stmt, ...]
    ) -> BindStep:
        ranks = _ranks(body)
        types = _types(body)
        bound: dict[str, Cell] = {}
        for param, arg in zip(params, args, strict=False):
            rank = ranks.get(param.name, 0)
            by_ref = param.mode == "reference" if param.explicit else rank > 0
            declared = types.get(param.name)
            if rank:
                if not isinstance(arg, NameExpr):
                    self._fail(
                        "E0312",
                        f"El parámetro {param.name} espera un arreglo.",
                        arg.span,
                        "Pasa el nombre del arreglo.",
                    )
                source = self._array_cell(arg.name, arg.span)
                if source.array is None:
                    self._fail("E0303", f"{arg.name} no es un arreglo.", arg.span, None)
                if by_ref:
                    bound[param.name] = source
                else:
                    copied = ArrayValue(
                        source.array.type_name,
                        source.array.lengths,
                        source.array.base,
                        list(source.array.cells),
                    )
                    if self.allocated_cells + len(copied.cells) > self.limits.max_array_cells:
                        self._fail(
                            "E0413",
                            "La copia del arreglo supera el número de celdas permitido.",
                            arg.span,
                            "Pásalo Por Referencia o reduce su tamaño.",
                        )
                    self.allocated_cells += len(copied.cells)
                    bound[param.name] = Cell(
                        copied.type_name, array=copied, dimensions=len(copied.lengths)
                    )
                continue
            if by_ref:
                bound[param.name] = yield from self._reference_cell(arg, declared)
                continue
            value = yield from self._eval(arg)
            target = declared or value.type_name
            cell = Cell(target)
            cell.value = self._coerce(target, value, arg.span)
            bound[param.name] = cell
        return bound

    def _reference_cell(self, arg: Expr, declared: TypeName | None) -> CellStep:
        if isinstance(arg, NameExpr):
            cell = self.cells.get(arg.name)
            if cell is None or cell.array is not None:
                self._fail(
                    "E0312",
                    f"{arg.name} no es una variable que se pueda pasar por referencia.",
                    arg.span,
                    "Pasa un escalar o un elemento del arreglo.",
                )
            return cell
        if isinstance(arg, IndexExpr):
            array_cell = self._array_cell(arg.name, arg.span)
            if array_cell.array is None:
                self._fail("E0303", f"{arg.name} no es un arreglo.", arg.span, None)
            offset = yield from self._offset(array_cell.array, arg.indexes, arg.span)
            return Cell(
                declared or array_cell.type_name,
                slot_owner=array_cell.array,
                slot_index=offset,
            )
        self._fail(
            "E0312",
            "Un parámetro por referencia necesita una variable.",
            arg.span,
            "Pasa una variable, no un cálculo.",
        )

    def _load_index(self, expr: IndexExpr) -> ValueStep:
        array_cell = self._array_cell(expr.name, expr.span)
        if array_cell.array is None:
            self._fail("E0303", f"{expr.name} no es un arreglo.", expr.span, None)
        offset = yield from self._offset(array_cell.array, expr.indexes, expr.span)
        return array_cell.array.cells[offset]

    def _array_cell(self, name: str, span: SourceSpan) -> Cell:
        cell = self.cells.get(name)
        if cell is None:
            self._fail(
                "E0301",
                f"La variable {name} no está declarada.",
                span,
                f"Agrégala con Dimension {name}[1] Como Entero;",
            )
        if cell.array is None:
            self._fail(
                "E0303",
                f"{name} no es un arreglo.",
                span,
                "Decláralo con Dimension.",
            )
        return cell

    def _offset(self, array: ArrayValue, indexes: tuple[Expr, ...], span: SourceSpan) -> IndexStep:
        if len(indexes) != len(array.lengths):
            self._fail(
                "E0313",
                f"Se esperaban {len(array.lengths)} índices y llegaron {len(indexes)}.",
                span,
                "Escribe un índice por cada dimensión.",
            )
        offset = 0
        for length, expr in zip(array.lengths, indexes, strict=True):
            index = self._require_int(
                (yield from self._eval(expr)),
                expr.span,
                "El índice debe ser Entero.",
            )
            last = array.base + length - 1
            if index < array.base or index > last:
                self._fail(
                    "E0404",
                    f"El índice {index} está fuera del intervalo {array.base}..{last}.",
                    expr.span,
                    "Revisa el tamaño declarado en Dimension.",
                )
            offset = offset * length + (index - array.base)
        return offset

    def _snapshot(self) -> dict[str, str]:
        visible: dict[str, str] = {}
        for name, cell in self.cells.items():
            if cell.array is not None:
                visible[name] = format_array(cell.array)
            elif cell.slot_owner is not None and cell.slot_index is not None:
                slot = cell.slot_owner.cells[cell.slot_index]
                visible[name] = format_value(slot.type_name, slot.value)
            elif cell.value is not None:
                visible[name] = format_value(cell.value.type_name, cell.value.value)
        return visible

    def _diagnostic(
        self,
        severity: Literal["error", "warning", "info"],
        code: str,
        message: str,
        span: SourceSpan,
        suggestion: str | None,
    ) -> Diagnostic:
        return make_diagnostic(self.source, severity, code, message, span, suggestion)

    def _fail(self, code: str, message: str, span: SourceSpan, suggestion: str | None) -> NoReturn:
        raise ExecFault(self._diagnostic("error", code, message, span, suggestion))


def _enters(current: int, end: int, step: int) -> bool:
    if step > 0:
        return current <= end
    return current >= end


def _as_decimal(value: Value) -> Decimal:
    if isinstance(value.value, Decimal):
        return value.value
    if isinstance(value.value, int):
        return Decimal(value.value)
    raise ExecFault(
        make_diagnostic(
            "",
            "error",
            "E0305",
            "Esta operación solo acepta números.",
            SourceSpan(1, 1, 1, 1),
            None,
        )
    )


def _int_op(operator: str, left: int, right: int) -> int:
    if operator == "add":
        return left + right
    if operator == "sub":
        return left - right
    return left * right


def _decimal_op(operator: str, left: Decimal, right: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 28
        if operator == "add":
            return left + right
        if operator == "sub":
            return left - right
        return left * right


def _ordered(operator: str, left: object, right: object) -> bool:
    if operator == "eq":
        return left == right
    if operator == "neq":
        return left != right
    if operator == "lt":
        return left < right  # type: ignore[operator]
    if operator == "lte":
        return left <= right  # type: ignore[operator]
    if operator == "gt":
        return left > right  # type: ignore[operator]
    return left >= right  # type: ignore[operator]


def _input_suggestion(type_name: str) -> str:
    suggestions = {
        "entero": "Escribe un número entero, por ejemplo 18.",
        "real": "Escribe un número con punto, por ejemplo 9.5.",
        "logico": "Escribe Verdadero o Falso.",
        "caracter": "Escribe un solo símbolo, por ejemplo A.",
        "cadena": "Escribe el texto en una línea.",
    }
    return suggestions.get(type_name, "Revisa el tipo de la variable.")


def _default_value(type_name: TypeName) -> Value:
    if type_name == "entero":
        return Value("entero", 0)
    if type_name == "real":
        return Value("real", Decimal(0))
    if type_name == "logico":
        return Value("logico", False)
    if type_name == "caracter":
        return Value("caracter", " ")
    return Value("cadena", "")


def _types(statements: tuple[Stmt, ...]) -> dict[str, TypeName]:
    found: dict[str, TypeName] = {}

    def visit(body: tuple[Stmt, ...]) -> None:
        for statement in body:
            if isinstance(statement, DefineStmt):
                for name in statement.names:
                    found.setdefault(name, statement.type_name)
            elif isinstance(statement, DimensionStmt):
                for decl in statement.declarations:
                    if decl.type_name is not None:
                        found.setdefault(decl.name, decl.type_name)
            elif isinstance(statement, IfStmt):
                visit(statement.then_body)
                if statement.else_body is not None:
                    visit(statement.else_body)
            elif isinstance(statement, (WhileStmt, RepeatStmt, ForStmt)):
                visit(statement.body)
            elif isinstance(statement, SwitchStmt):
                for case in statement.cases:
                    visit(case.body)
                if statement.default_body is not None:
                    visit(statement.default_body)

    visit(statements)
    return found


def _ranks(statements: tuple[Stmt, ...]) -> dict[str, int]:
    found: dict[str, int] = {}

    def visit(body: tuple[Stmt, ...]) -> None:
        for statement in body:
            if isinstance(statement, DimensionStmt):
                for decl in statement.declarations:
                    found.setdefault(decl.name, len(decl.lengths))
            elif isinstance(statement, IfStmt):
                visit(statement.then_body)
                if statement.else_body is not None:
                    visit(statement.else_body)
            elif isinstance(statement, (WhileStmt, RepeatStmt, ForStmt)):
                visit(statement.body)
            elif isinstance(statement, SwitchStmt):
                for case in statement.cases:
                    visit(case.body)
                if statement.default_body is not None:
                    visit(statement.default_body)

    visit(statements)
    return found
