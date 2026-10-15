"""Análisis semántico.

El ámbito es el algoritmo o la subrutina, no el bloque. Los arreglos, Segun,
las llamadas y la biblioteca se comprueban aquí. El AST no se modifica.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from language_core.ast_nodes import (
    AssignStmt,
    CallExpr,
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
from language_core.diagnostics import Diagnostic, make_diagnostic
from language_core.grammar import STDLIB_NAMES, LanguageProfile, canonicalize
from language_core.stdlib import std_arity, std_return_type
from language_core.type_system import (
    TypeIssue,
    check_assignment,
    check_binary,
    check_condition,
    check_unary,
)

SymbolKind = Literal["scalar", "array", "function", "procedure", "parameter"]
PassMode = Literal["value", "reference"]
RoutineKind = Literal["function", "procedure"]


@dataclass(frozen=True)
class Symbol:
    """Un nombre visible en el algoritmo o en una subrutina."""

    name: str
    kind: SymbolKind
    type_name: TypeName | None
    dimensions: int | None
    mode: PassMode | None
    declared_at: SourceSpan


@dataclass(frozen=True)
class Routine:
    """Firma ya recogida, antes de revisar el cuerpo."""

    kind: RoutineKind
    name: str
    params: tuple[Param, ...]
    result_name: str | None
    result_type: TypeName | None
    param_types: dict[str, TypeName | None]
    param_ranks: dict[str, int]
    span: SourceSpan


class SemanticAnalyzer:
    """Recorre el AST y acumula diagnósticos sin ejecutarlo."""

    def __init__(self, program: Program, profile: LanguageProfile, source: str) -> None:
        self.program = program
        self.profile = profile
        self.source = source
        self.symbols: dict[str, Symbol] = {}
        self.routines: dict[str, Routine] = {}
        self.reads: set[str] = set()
        self.writes: set[str] = set()
        self.result_name: str | None = None
        self.diagnostics: list[Diagnostic] = []

    def analyze(self) -> tuple[Diagnostic, ...]:
        self._register_routines()
        for function in self.program.functions:
            routine = self.routines.get(function.name)
            if routine is not None and routine.kind == "function":
                self._analyze_routine(function.body, routine)
        for procedure in self.program.procedures:
            routine = self.routines.get(procedure.name)
            if routine is not None and routine.kind == "procedure":
                self._analyze_routine(procedure.body, routine)
        self._open_scope(None)
        self._statements(self.program.algorithm.body)
        if self.profile.beginner_warnings:
            self._warn_unused()
        return tuple(self.diagnostics)

    def _register_routines(self) -> None:
        seen: dict[str, SourceSpan] = {}
        for function in self.program.functions:
            self._add_routine(
                Routine(
                    "function",
                    function.name,
                    function.params,
                    function.result_name,
                    _find_type(function.body, function.result_name),
                    _param_types(function.body, function.params),
                    _param_ranks(function.body, function.params),
                    function.span,
                ),
                seen,
            )
        for procedure in self.program.procedures:
            self._add_routine(
                Routine(
                    "procedure",
                    procedure.name,
                    procedure.params,
                    None,
                    None,
                    _param_types(procedure.body, procedure.params),
                    _param_ranks(procedure.body, procedure.params),
                    procedure.span,
                ),
                seen,
            )

    def _add_routine(self, routine: Routine, seen: dict[str, SourceSpan]) -> None:
        if canonicalize(routine.name) in STDLIB_NAMES:
            self._error(
                "E0307",
                f"{routine.name} es un nombre de la biblioteca y no puede redefinirse.",
                routine.span,
                "Elige otro nombre para la función o el procedimiento.",
            )
            return
        previous = seen.get(routine.name)
        if previous is not None:
            self._error(
                "E0302",
                f"{routine.name} ya está declarado.",
                routine.span,
                "Usa un nombre distinto para cada función y procedimiento.",
            )
            return
        seen[routine.name] = routine.span
        self.routines[routine.name] = routine

    def _analyze_routine(self, body: tuple[Stmt, ...], routine: Routine) -> None:
        self._open_scope(routine)
        self._statements(body)
        if routine.result_name is not None:
            self.reads.add(routine.result_name)
            assigned = _definitely_assigned(body, {param.name for param in routine.params})
            if routine.result_name not in assigned:
                self._error(
                    "E0309",
                    f"La función {routine.name} no asigna {routine.result_name} en todos los caminos.",
                    routine.span,
                    f"Asigna {routine.result_name} antes de FinFuncion, también en el Sino.",
                )
        if self.profile.beginner_warnings:
            self._warn_unused()

    def _open_scope(self, routine: Routine | None) -> None:
        self.symbols = {}
        self.reads = set()
        self.writes = set()
        self.result_name = None if routine is None else routine.result_name
        if routine is None:
            return
        for param in routine.params:
            self.symbols[param.name] = Symbol(
                param.name,
                "parameter",
                routine.param_types.get(param.name),
                routine.param_ranks.get(param.name) or None,
                (
                    "reference"
                    if _by_reference(param, routine.param_ranks.get(param.name, 0))
                    else "value"
                ),
                param.span,
            )

    def _statements(self, statements: tuple[Stmt, ...]) -> None:
        for statement in statements:
            self._statement(statement)

    def _statement(self, statement: Stmt) -> None:
        if isinstance(statement, DefineStmt):
            self._define(statement)
        elif isinstance(statement, DimensionStmt):
            self._dimension(statement)
        elif isinstance(statement, AssignStmt):
            self._assign(statement)
        elif isinstance(statement, ReadStmt):
            self._read(statement)
        elif isinstance(statement, WriteStmt):
            for value in statement.values:
                self._expr(value)
        elif isinstance(statement, ClearStmt):
            return
        elif isinstance(statement, WaitStmt):
            self._expect_numero(statement.seconds, "La espera debe ser un número.")
        elif isinstance(statement, IfStmt):
            self._condition(statement.condition)
            self._statements(statement.then_body)
            if statement.else_body is not None:
                self._statements(statement.else_body)
        elif isinstance(statement, WhileStmt):
            self._condition(statement.condition)
            self._statements(statement.body)
        elif isinstance(statement, RepeatStmt):
            self._statements(statement.body)
            self._condition(statement.condition)
        elif isinstance(statement, ForStmt):
            self._for(statement)
        elif isinstance(statement, SwitchStmt):
            self._switch(statement)
        else:
            self._call(statement.call, as_statement=True)

    def _define(self, statement: DefineStmt) -> None:
        for name, span in zip(statement.names, statement.name_spans, strict=True):
            if self._clashes_with_library(name, span):
                continue
            current = self.symbols.get(name)
            if (
                current is not None
                and current.type_name is not None
                and current.kind != "parameter"
            ):
                self._error(
                    "E0302",
                    f"La variable {name} ya está declarada en este ámbito.",
                    span,
                    "Usa un nombre nuevo o elimina la definición repetida.",
                )
                continue
            if (
                current is not None
                and current.kind == "parameter"
                and current.type_name
                not in (
                    None,
                    statement.type_name,
                )
            ):
                self._error(
                    "E0303",
                    f"El parámetro {name} ya tiene otro tipo.",
                    span,
                    "Usa el mismo tipo en el Definir y en Dimension.",
                )
                continue
            kind: SymbolKind = (
                current.kind if current is not None and current.kind == "parameter" else "scalar"
            )
            dimensions = None if current is None else current.dimensions
            mode = None if current is None else current.mode
            self.symbols[name] = Symbol(name, kind, statement.type_name, dimensions, mode, span)

    def _dimension(self, statement: DimensionStmt) -> None:
        for decl in statement.declarations:
            if len(decl.lengths) > 4:
                self._error(
                    "E0313",
                    "Un arreglo admite como máximo 4 dimensiones.",
                    decl.span,
                    "Divide el dato en arreglos más chicos.",
                )
            for length in decl.lengths:
                self._expect_entero(length, "El tamaño de una dimensión debe ser Entero.")
            if self._clashes_with_library(decl.name, decl.span):
                continue
            current = self.symbols.get(decl.name)
            element = decl.type_name
            if current is not None and current.type_name is not None:
                if element is not None and element != current.type_name:
                    self._error(
                        "E0303",
                        f"El arreglo {decl.name} no coincide con el tipo declarado.",
                        decl.span,
                        "Usa el mismo tipo en Definir y en Dimension.",
                    )
                    continue
                element = element or current.type_name
            if element is None:
                if self.profile.require_declarations:
                    self._error(
                        "E0314",
                        f"Falta el tipo del arreglo {decl.name}.",
                        decl.span,
                        f"Escríbelo así: Dimension {decl.name}[{_size_hint(decl.lengths)}] Como Entero;",
                    )
                    continue
                element = "entero"
            kind: SymbolKind = (
                "parameter" if current is not None and current.kind == "parameter" else "array"
            )
            mode = None if current is None else current.mode
            origin = decl.span if current is None else current.declared_at
            self.symbols[decl.name] = Symbol(
                decl.name, kind, element, len(decl.lengths), mode, origin
            )

    def _assign(self, statement: AssignStmt) -> None:
        if statement.target.indexes:
            self._index_target(
                statement.target.name, statement.target.indexes, statement.target.span
            )
            source = self._expr(statement.value)
            symbol = self.symbols.get(statement.target.name)
            if source is not None and symbol is not None and symbol.type_name is not None:
                for issue in check_assignment(
                    symbol.type_name,
                    source,
                    statement.value,
                    implicit_widening=self.profile.implicit_widening,
                ):
                    self._from_issue(issue, statement.span)
            self.writes.add(statement.target.name)
            return
        source = self._expr(statement.value)
        name = statement.target.name
        if self._clashes_with_library(name, statement.target.span):
            return
        symbol = self.symbols.get(name)
        if symbol is None:
            if self.profile.require_declarations or source is None:
                self._undeclared(name, statement.target.span)
                return
            self.symbols[name] = Symbol(name, "scalar", source, None, None, statement.target.span)
            self.writes.add(name)
            return
        if symbol.dimensions:
            self._error(
                "E0303",
                f"Al arreglo {name} le falta el índice.",
                statement.target.span,
                f"Escribe {name}[1] <- ...;",
            )
            return
        if source is not None and symbol.type_name is not None:
            for issue in check_assignment(
                symbol.type_name,
                source,
                statement.value,
                implicit_widening=self.profile.implicit_widening,
            ):
                self._from_issue(issue, statement.span)
        self.writes.add(name)

    def _read(self, statement: ReadStmt) -> None:
        for target in statement.targets:
            if target.indexes:
                self._index_target(target.name, target.indexes, target.span)
                self.writes.add(target.name)
                continue
            if self._clashes_with_library(target.name, target.span):
                continue
            if target.name not in self.symbols:
                if self.profile.require_declarations:
                    self._undeclared(target.name, target.span)
                else:
                    self.symbols[target.name] = Symbol(
                        target.name, "scalar", "cadena", None, None, target.span
                    )
            self.writes.add(target.name)

    def _for(self, statement: ForStmt) -> None:
        symbol = self.symbols.get(statement.variable)
        if symbol is None:
            if self.profile.require_declarations:
                self._undeclared(statement.variable, statement.variable_span)
            else:
                symbol = Symbol(
                    statement.variable, "scalar", "entero", None, None, statement.variable_span
                )
                self.symbols[statement.variable] = symbol
        elif symbol.type_name not in (None, "entero") or symbol.dimensions:
            self._error(
                "E0308",
                f"La variable {statement.variable} debe ser Entero para usarla en Para.",
                statement.variable_span,
                "Declárala con Definir i Como Entero;",
            )
        self.reads.add(statement.variable)
        self.writes.add(statement.variable)
        self._expect_entero(statement.start, "El inicio del Para debe ser Entero.")
        self._expect_entero(statement.end, "El límite del Para debe ser Entero.")
        if statement.step is not None:
            self._expect_entero(statement.step, "El paso del Para debe ser Entero.")
        self._statements(statement.body)

    def _switch(self, statement: SwitchStmt) -> None:
        selector = self._expr(statement.selector)
        seen: set[object] = set()
        for case in statement.cases:
            for label in case.labels:
                folded = _signed_label(label)
                if folded is None:
                    self._error(
                        "E0315",
                        "La etiqueta de Segun debe ser un literal.",
                        label.span,
                        "Escribe un número, un texto o Verdadero, no una expresión.",
                    )
                else:
                    key = _label_key(folded)
                    if key in seen:
                        self._error(
                            "E0316",
                            "Esa etiqueta ya apareció en este Segun.",
                            label.span,
                            "Deja cada valor en un solo caso.",
                        )
                    seen.add(key)
                    if selector is not None and not _compatible(selector, folded.kind):
                        self._error(
                            "E0306",
                            "La etiqueta no se puede comparar con el valor del Segun.",
                            label.span,
                            "Usa el mismo tipo de dato en el selector y en las etiquetas.",
                        )
            self._statements(case.body)
        if statement.default_body is not None:
            self._statements(statement.default_body)

    def _condition(self, expr: Expr) -> None:
        type_name = self._expr(expr)
        if type_name is None:
            return
        issue = check_condition(type_name)
        if issue is not None:
            self._from_issue(issue, expr.span)

    def _expect_numero(self, expr: Expr, message: str) -> None:
        type_name = self._expr(expr)
        if type_name is not None and type_name not in ("entero", "real"):
            self._error("E0303", message, expr.span, "Usa un Entero o un Real.")

    def _expect_entero(self, expr: Expr, message: str) -> None:
        type_name = self._expr(expr)
        if type_name is not None and type_name != "entero":
            self._error("E0303", message, expr.span, "Usa un número sin decimales.")

    def _expr(self, expr: Expr) -> TypeName | None:
        if isinstance(expr, NameExpr):
            return self._name(expr)
        if isinstance(expr, IndexExpr):
            return self._index_target(expr.name, expr.indexes, expr.span)
        if isinstance(expr, CallExpr):
            return self._call(expr, as_statement=False)
        if isinstance(expr, LiteralExpr):
            return None if expr.raw == "?" else expr.kind
        if isinstance(expr, UnaryExpr):
            operand = self._expr(expr.operand)
            if operand is None:
                return None
            result, issues = check_unary(expr.operator, operand)
            for issue in issues:
                self._from_issue(issue, expr.span)
            return result
        left = self._expr(expr.left)
        right = self._expr(expr.right)
        if left is None or right is None:
            return None
        result, issues = check_binary(
            expr.operator,
            left,
            right,
            expr.right,
            beginner_warnings=self.profile.beginner_warnings,
        )
        for issue in issues:
            self._from_issue(issue, expr.span)
        return result

    def _name(self, expr: NameExpr) -> TypeName | None:
        if expr.name in self.routines or canonicalize(expr.name) in STDLIB_NAMES:
            self._error(
                "E0312",
                f"{expr.name} es una función: faltan los paréntesis.",
                expr.span,
                f"Escríbela como llamada, por ejemplo {expr.name}(1).",
            )
            return None
        symbol = self.symbols.get(expr.name)
        if symbol is None or symbol.type_name is None:
            self._undeclared(expr.name, expr.span)
            return None
        if symbol.dimensions:
            self._error(
                "E0303",
                f"Al arreglo {expr.name} le falta el índice.",
                expr.span,
                f"Escribe {expr.name}[1].",
            )
            return None
        self.reads.add(expr.name)
        return symbol.type_name

    def _index_target(
        self, name: str, indexes: tuple[Expr, ...], span: SourceSpan
    ) -> TypeName | None:
        for index in indexes:
            self._expect_entero(index, "El índice debe ser Entero.")
        symbol = self.symbols.get(name)
        if symbol is None or symbol.type_name is None:
            self._undeclared(name, span)
            return None
        if not symbol.dimensions:
            self._error(
                "E0303",
                f"{name} no es un arreglo.",
                span,
                "Quita los corchetes o decláralo con Dimension.",
            )
            return None
        if len(indexes) != symbol.dimensions:
            self._error(
                "E0313",
                f"{name} tiene {symbol.dimensions} dimensiones y aquí hay {len(indexes)} índices.",
                span,
                "Escribe un índice por cada dimensión.",
            )
        self.reads.add(name)
        return symbol.type_name

    def _call(self, call: CallExpr, *, as_statement: bool) -> TypeName | None:
        library = std_arity(call.name)
        routine = self.routines.get(call.name)
        if library is None and routine is None:
            self._error(
                "E0310",
                f"No existe la función o el procedimiento {call.name}.",
                call.span,
                "Revisa el nombre y que esté escrito antes o después del algoritmo.",
            )
            for arg in call.args:
                self._expr(arg)
            return None
        if routine is not None and routine.kind == "procedure" and not as_statement:
            self._error(
                "E0312",
                f"{call.name} es un procedimiento y no devuelve un valor.",
                call.span,
                "Úsalo como sentencia, en su propia línea.",
            )
        if library is not None:
            minimum, maximum = library
            expected = maximum if minimum == maximum else None
            self._check_arity(call, minimum, maximum, expected)
            arg_types = [self._expr(arg) for arg in call.args]
            return std_return_type(call.name, arg_types)
        assert routine is not None
        self._check_arity(call, len(routine.params), len(routine.params), len(routine.params))
        if len(call.args) != len(routine.params):
            for arg in call.args:
                self._expr(arg)
            return routine.result_type
        for param, arg in zip(routine.params, call.args, strict=True):
            self._check_argument(routine, param, arg)
        return routine.result_type

    def _check_arity(
        self, call: CallExpr, minimum: int, maximum: int, expected: int | None
    ) -> None:
        count = len(call.args)
        if minimum <= count <= maximum:
            return
        if expected is None:
            detail = f"entre {minimum} y {maximum} argumentos"
        else:
            detail = f"{expected} argumentos"
        self._error(
            "E0311",
            f"{call.name} espera {detail} y recibió {count}.",
            call.span,
            "Revisa la lista entre paréntesis.",
        )

    def _check_argument(self, routine: Routine, param: Param, arg: Expr) -> None:
        rank = routine.param_ranks.get(param.name, 0)
        expected = routine.param_types.get(param.name)
        by_ref = _by_reference(param, rank)
        if rank:
            if not isinstance(arg, NameExpr):
                self._error(
                    "E0312",
                    f"El parámetro {param.name} espera un arreglo.",
                    arg.span,
                    "Pasa el nombre del arreglo, sin índice.",
                )
                return
            symbol = self.symbols.get(arg.name)
            if symbol is None or not symbol.dimensions:
                self._error(
                    "E0303",
                    f"{arg.name} no es un arreglo.",
                    arg.span,
                    f"Decláralo con Dimension antes de pasarlo a {routine.name}.",
                )
                return
            if symbol.dimensions != rank:
                self._error(
                    "E0313",
                    f"{arg.name} no tiene las mismas dimensiones que {param.name}.",
                    arg.span,
                    "El arreglo y el parámetro deben tener la misma cantidad de dimensiones.",
                )
            if expected is not None and symbol.type_name not in (None, expected):
                self._error(
                    "E0303",
                    f"El tipo de {arg.name} no coincide con el parámetro {param.name}.",
                    arg.span,
                    "Usa el mismo tipo en ambos Dimension.",
                )
            self.reads.add(arg.name)
            return
        if by_ref and not isinstance(arg, (NameExpr, IndexExpr)):
            self._error(
                "E0312",
                f"El parámetro {param.name} es por referencia y necesita una variable.",
                arg.span,
                "Pasa una variable, no un cálculo.",
            )
            return
        actual = self._expr(arg)
        if expected is not None and actual is not None:
            for issue in check_assignment(
                expected,
                actual,
                arg,
                implicit_widening=self.profile.implicit_widening,
            ):
                self._from_issue(issue, arg.span)

    def _clashes_with_library(self, name: str, span: SourceSpan) -> bool:
        if canonicalize(name) not in STDLIB_NAMES and name not in self.routines:
            return False
        if name in self.symbols:
            return False
        self._error(
            "E0307",
            f"{name} es un nombre de la biblioteca o de una subrutina y no puede ser una variable.",
            span,
            "Elige otro nombre.",
        )
        return True

    def _undeclared(self, name: str, span: SourceSpan) -> None:
        self._error(
            "E0301",
            f"La variable {name} no está declarada.",
            span,
            f"Agrégala antes, por ejemplo: Definir {name} Como Entero;",
        )

    def _warn_unused(self) -> None:
        for name, symbol in self.symbols.items():
            if (
                symbol.kind not in ("scalar", "array")
                or name in self.reads
                or name == self.result_name
            ):
                continue
            self._emit(
                "warning",
                "W0503",
                f"La variable {name} no se usa.",
                symbol.declared_at,
                "Léela en una expresión o elimina la declaración.",
            )

    def _error(self, code: str, message: str, span: SourceSpan, suggestion: str | None) -> None:
        self._emit("error", code, message, span, suggestion)

    def _from_issue(self, issue: TypeIssue, span: SourceSpan) -> None:
        if issue.severity == "warning":
            self._emit("warning", issue.code, issue.message, span, issue.suggestion)
            return
        self._emit("error", issue.code, issue.message, span, issue.suggestion)

    def _emit(
        self,
        severity: Literal["error", "warning", "info"],
        code: str,
        message: str,
        span: SourceSpan,
        suggestion: str | None,
    ) -> None:
        self.diagnostics.append(
            make_diagnostic(self.source, severity, code, message, span, suggestion)
        )


def analyze(program: Program, profile: LanguageProfile, source: str) -> tuple[Diagnostic, ...]:
    """Analiza `program` y devuelve los diagnósticos semánticos."""
    return SemanticAnalyzer(program, profile, source).analyze()


def _by_reference(param: Param, rank: int) -> bool:
    if param.explicit:
        return param.mode == "reference"
    return rank > 0


def _find_type(statements: tuple[Stmt, ...], name: str) -> TypeName | None:
    return _collect_types(statements).get(name)


def _param_types(
    statements: tuple[Stmt, ...], params: tuple[Param, ...]
) -> dict[str, TypeName | None]:
    found = _collect_types(statements)
    return {param.name: found.get(param.name) for param in params}


def _param_ranks(statements: tuple[Stmt, ...], params: tuple[Param, ...]) -> dict[str, int]:
    found = _collect_ranks(statements)
    return {param.name: found.get(param.name, 0) for param in params}


def _collect_types(statements: tuple[Stmt, ...]) -> dict[str, TypeName]:
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
            else:
                visit(_nested(statement))

    visit(statements)
    return found


def _collect_ranks(statements: tuple[Stmt, ...]) -> dict[str, int]:
    found: dict[str, int] = {}

    def visit(body: tuple[Stmt, ...]) -> None:
        for statement in body:
            if isinstance(statement, DimensionStmt):
                for decl in statement.declarations:
                    found.setdefault(decl.name, len(decl.lengths))
            else:
                visit(_nested(statement))

    visit(statements)
    return found


def _nested(statement: Stmt) -> tuple[Stmt, ...]:
    if isinstance(statement, IfStmt):
        return statement.then_body + (statement.else_body or ())
    if isinstance(statement, (WhileStmt, RepeatStmt, ForStmt)):
        return statement.body
    if isinstance(statement, SwitchStmt):
        bodies: list[Stmt] = []
        for case in statement.cases:
            bodies.extend(case.body)
        if statement.default_body is not None:
            bodies.extend(statement.default_body)
        return tuple(bodies)
    return ()


def _definitely_assigned(statements: tuple[Stmt, ...], already: set[str]) -> set[str]:
    current = set(already)
    for statement in statements:
        current = _assigned_by(statement, current)
    return current


def _assigned_by(statement: Stmt, current: set[str]) -> set[str]:
    if isinstance(statement, AssignStmt) and not statement.target.indexes:
        return current | {statement.target.name}
    if isinstance(statement, ReadStmt):
        names = {target.name for target in statement.targets if not target.indexes}
        return current | names
    if isinstance(statement, DimensionStmt):
        return current | {decl.name for decl in statement.declarations}
    if isinstance(statement, IfStmt):
        if statement.else_body is None:
            return set(current)
        then_names = _definitely_assigned(statement.then_body, current)
        else_names = _definitely_assigned(statement.else_body, current)
        return then_names & else_names
    if isinstance(statement, RepeatStmt):
        return _definitely_assigned(statement.body, current)
    return set(current)


def _signed_label(label: Expr) -> LiteralExpr | None:
    """Un literal, o el signo de un número literal. -1 cuenta como el entero -1."""
    if isinstance(label, LiteralExpr):
        return label
    if (
        isinstance(label, UnaryExpr)
        and label.operator in ("neg", "pos")
        and isinstance(label.operand, LiteralExpr)
        and label.operand.kind in ("entero", "real")
    ):
        inner = label.operand
        negative = label.operator == "neg"
        if inner.kind == "entero" and isinstance(inner.value, int):
            raw = f"-{inner.raw}" if negative else inner.raw
            whole = -inner.value if negative else inner.value
            return LiteralExpr("entero", whole, raw, label.span)
        if inner.kind == "real" and isinstance(inner.value, Decimal):
            raw = f"-{inner.raw}" if negative else inner.raw
            real = -inner.value if negative else inner.value
            return LiteralExpr("real", real, raw, label.span)
    return None


def _label_key(label: LiteralExpr) -> object:
    if label.kind in ("entero", "real"):
        return ("num", Decimal(str(label.value)))
    return (label.kind, label.value)


def _compatible(selector: TypeName, label: TypeName) -> bool:
    if selector == label:
        return True
    return selector in ("entero", "real") and label in ("entero", "real")


def _size_hint(lengths: tuple[Expr, ...]) -> str:
    return ", ".join("n" for _ in lengths)
