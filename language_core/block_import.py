"""Pseudocódigo al JSON de bloques del laboratorio.

Usa el parser de siempre. Si el archivo usa un arreglo, una función o un
operador sin bloque, no devuelve un lienzo a medias.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import NoReturn

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
    FunctionDecl,
    IfStmt,
    IndexExpr,
    LiteralExpr,
    LValue,
    NameExpr,
    ProcedureDecl,
    Program,
    ReadStmt,
    RepeatStmt,
    SourceSpan,
    Stmt,
    SwitchStmt,
    UnaryExpr,
    WaitStmt,
    WhileStmt,
    WriteStmt,
)
from language_core.block_adapter import MAX_BLOCKS, MAX_DEPTH, MAX_SEGUN_CASES, MAX_WRITE_VALUES
from language_core.diagnostics import Diagnostic, make_diagnostic
from language_core.grammar import STRICT
from language_core.interpreter import compile_source
from language_core.pseudocode import format_real
from language_core.stdlib import std_arity, std_return_type

MAX_IMPORT_BYTES = 64 * 1024

_ARITH = frozenset({"add", "sub", "mul", "div", "idiv", "mod"})
_REL = frozenset({"eq", "neq", "lt", "lte", "gt", "gte"})
_LOGIC = frozenset({"and", "or"})


class _Refuse(Exception):
    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


@dataclass(frozen=True)
class Imported:
    """Lienzo listo para Blockly, o solo los diagnósticos si no se pudo armar."""

    workspace: dict[str, object] | None
    diagnostics: tuple[Diagnostic, ...]


def workspace_from_source(source: str) -> Imported:
    """Arma el JSON de `serialization.workspaces.load` a partir del texto."""
    text = source[1:] if source.startswith("\ufeff") else source
    if len(text.encode("utf-8")) > MAX_IMPORT_BYTES:
        return Imported(
            None,
            (_plain(text, "error", "El archivo supera 64 KiB.", "Elige un archivo más corto."),),
        )
    if not text.strip():
        return Imported(
            None,
            (_plain(text, "error", "El archivo está vacío.", "Elige un archivo de pseudocódigo."),),
        )
    compiled = compile_source(text, STRICT)
    program = compiled.program
    if program is None:
        return Imported(None, compiled.diagnostics)
    canvas = _Canvas(text)
    try:
        tops = canvas.convert(program)
    except _Refuse as refused:
        return Imported(None, (refused.diagnostic,))
    return Imported(_workspace(tops), tuple(canvas.warnings))


def _workspace(tops: list[dict[str, object]]) -> dict[str, object]:
    return {"blocks": {"languageVersion": 0, "blocks": tops}}


def _plain(source: str, severity: str, message: str, suggestion: str) -> Diagnostic:
    return _error(source, message, SourceSpan(1, 1, 1, 1), suggestion, severity=severity)


def _error(
    source: str,
    message: str,
    span: SourceSpan,
    suggestion: str,
    *,
    severity: str = "error",
    code: str = "L0001",
) -> Diagnostic:
    if severity == "warning":
        return make_diagnostic(source, "warning", code, message, span, suggestion)
    return make_diagnostic(source, "error", code, message, span, suggestion)


@dataclass
class _Canvas:
    source: str
    ids: int = 0
    depth: int = 0
    types: dict[str, str] = field(default_factory=dict)
    results: dict[str, str] = field(default_factory=dict)
    warnings: list[Diagnostic] = field(default_factory=list)

    def convert(self, program: Program) -> list[dict[str, object]]:
        for function in program.functions:
            self.results[function.name] = self._result_type(function.result_name, function.body)
            self._collect(function.body)
        for procedure in program.procedures:
            self._collect(procedure.body)
        self._collect(program.algorithm.body)
        tops = [self._function_block(function) for function in program.functions]
        tops.extend(self._procedure_block(procedure) for procedure in program.procedures)
        chain = self._sequence(program.algorithm.body)
        if chain is not None:
            tops.append(chain)
        if not tops:
            self.warnings.append(
                _error(
                    self.source,
                    "El algoritmo no tiene sentencias.",
                    program.algorithm.span,
                    "Agrega Definir, Leer o Escribir.",
                    severity="warning",
                    code="L0007",
                )
            )
        return tops

    def _collect(self, statements: tuple[Stmt, ...]) -> None:
        for statement in statements:
            if isinstance(statement, DefineStmt):
                for name in statement.names:
                    self.types.setdefault(name, statement.type_name)
            elif isinstance(statement, DimensionStmt):
                for decl in statement.declarations:
                    if decl.type_name is not None:
                        self.types.setdefault(decl.name, decl.type_name)
            elif isinstance(statement, IfStmt):
                self._collect(statement.then_body)
                if statement.else_body is not None:
                    self._collect(statement.else_body)
            elif isinstance(statement, WhileStmt):
                self._collect(statement.body)
            elif isinstance(statement, RepeatStmt):
                self._collect(statement.body)
            elif isinstance(statement, ForStmt):
                self._collect(statement.body)
            elif isinstance(statement, SwitchStmt):
                for case in statement.cases:
                    self._collect(case.body)
                if statement.default_body is not None:
                    self._collect(statement.default_body)

    def _sequence(self, statements: tuple[Stmt, ...]) -> dict[str, object] | None:
        built: list[dict[str, object]] = []
        for statement in statements:
            built.extend(self._statement(statement))
        if not built:
            return None
        for earlier, later in zip(built, built[1:], strict=False):
            earlier["next"] = {"block": later}
        return built[0]

    def _statement(self, statement: Stmt) -> list[dict[str, object]]:
        self._enter(statement.span, "Hay demasiados bloques anidados.", "Saca un bloque afuera.")
        try:
            return self._statement_body(statement)
        finally:
            self.depth -= 1

    def _statement_body(self, statement: Stmt) -> list[dict[str, object]]:
        if isinstance(statement, DefineStmt):
            return [
                self._block(
                    "traza_definir",
                    statement.span,
                    {"NOMBRE": name, "TIPO": statement.type_name},
                )
                for name in statement.names
            ]
        if isinstance(statement, AssignStmt):
            if statement.target.indexes:
                return [
                    self._indexed(
                        "traza_asignar_indice", statement.target, statement.span, statement.value
                    )
                ]
            return [
                self._block(
                    "traza_asignar",
                    statement.span,
                    {"NOMBRE": statement.target.name},
                    {"VALOR": _slot(self._expr(statement.value))},
                )
            ]
        if isinstance(statement, ReadStmt):
            blocks: list[dict[str, object]] = []
            for target in statement.targets:
                if target.indexes:
                    blocks.append(self._indexed("traza_leer_indice", target, statement.span, None))
                else:
                    blocks.append(
                        self._block("traza_leer", statement.span, {"NOMBRE": target.name})
                    )
            return blocks
        if isinstance(statement, WriteStmt):
            if len(statement.values) > MAX_WRITE_VALUES:
                self._stop(
                    "Escribir: el lienzo admite hasta 8 valores.",
                    statement.span,
                    "Separa el resto en otro Escribir.",
                )
            slots: dict[str, object] = {
                "VALOR" if index == 1 else f"VALOR{index}": _slot(self._expr(value))
                for index, value in enumerate(statement.values, start=1)
            }
            extra: dict[str, object] | None = (
                {"valores": len(statement.values)} if len(statement.values) > 1 else None
            )
            fields: dict[str, object] | None = None if statement.newline else {"SIN_SALTAR": "TRUE"}
            return [self._block("traza_escribir", statement.span, fields, slots, extra)]
        if isinstance(statement, ClearStmt):
            return [self._block("traza_borrar_pantalla", statement.span)]
        if isinstance(statement, WaitStmt):
            return [
                self._block(
                    "traza_esperar",
                    statement.span,
                    inputs={"SEGUNDOS": _slot(self._expr(statement.seconds))},
                )
            ]
        if isinstance(statement, IfStmt):
            inputs: dict[str, object] = {"CONDICION": _slot(self._expr(statement.condition))}
            self._body(inputs, "ENTONCES", statement.then_body)
            if statement.else_body is None:
                return [self._block("traza_si", statement.span, inputs=inputs)]
            self._body(inputs, "SINO", statement.else_body)
            return [self._block("traza_si_sino", statement.span, inputs=inputs)]
        if isinstance(statement, WhileStmt):
            inputs = {"CONDICION": _slot(self._expr(statement.condition))}
            self._body(inputs, "CUERPO", statement.body)
            return [self._block("traza_mientras", statement.span, inputs=inputs)]
        if isinstance(statement, RepeatStmt):
            inputs = {"CONDICION": _slot(self._expr(statement.condition))}
            self._body(inputs, "CUERPO", statement.body)
            return [self._block("traza_repetir", statement.span, inputs=inputs)]
        if isinstance(statement, ForStmt):
            return [self._for(statement)]
        if isinstance(statement, SwitchStmt):
            return [self._switch(statement)]
        if isinstance(statement, DimensionStmt):
            blocks = []
            for decl in statement.declarations:
                if decl.type_name is None:
                    self._stop(
                        "Arreglos: falta el tipo en Dimension.",
                        decl.span,
                        "Escríbelo con Como y un tipo.",
                    )
                if not 1 <= len(decl.lengths) <= 4:
                    self._stop(
                        "Arreglos: el lienzo admite de 1 a 4 dimensiones.",
                        decl.span,
                        "Parte el arreglo en menos dimensiones.",
                    )
                inputs = {
                    f"TAMANO{index}": _slot(self._expr(length))
                    for index, length in enumerate(decl.lengths, start=1)
                }
                blocks.append(
                    self._block(
                        "traza_dimension",
                        decl.span,
                        {"NOMBRE": decl.name, "TIPO": decl.type_name},
                        inputs,
                        {"dimensiones": len(decl.lengths)},
                    )
                )
            return blocks
        if isinstance(statement, CallStmt):
            return [self._call_block("traza_llamar", statement.call, statement.span, None)]
        self._stop(
            "El lienzo no tiene un bloque para esa sentencia.",
            statement.span,
            "Usa los bloques de la caja.",
        )

    def _indexed(
        self, kind: str, target: LValue, span: SourceSpan, value: Expr | None
    ) -> dict[str, object]:
        return self._index_slots(kind, target.name, target.indexes, span, value)

    def _index_block(self, expr: IndexExpr) -> dict[str, object]:
        return self._index_slots("traza_indice", expr.name, expr.indexes, expr.span, None)

    def _index_slots(
        self,
        kind: str,
        name: str,
        indexes: tuple[Expr, ...],
        span: SourceSpan,
        value: Expr | None,
    ) -> dict[str, object]:
        if not 1 <= len(indexes) <= 4:
            self._stop(
                "Arreglos: el lienzo admite de 1 a 4 índices.",
                span,
                "Usa un índice por cada dimensión.",
            )
        fields: dict[str, object] = {"NOMBRE": name}
        if kind == "traza_indice":
            fields["TIPO"] = self.types.get(name, "entero")
        inputs: dict[str, object] = {
            f"INDICE{index}": _slot(self._expr(item)) for index, item in enumerate(indexes, start=1)
        }
        if value is not None:
            inputs["VALOR"] = _slot(self._expr(value))
        return self._block(kind, span, fields, inputs, {"dimensiones": len(indexes)})

    def _call_type(self, expr: CallExpr) -> str:
        found = self.results.get(expr.name)
        if found is not None:
            return found
        if std_arity(expr.name) is None:
            return "entero"
        returned = std_return_type(expr.name, [None] * len(expr.args))
        return returned if returned is not None else "entero"

    def _call_block(
        self, kind: str, call: CallExpr, span: SourceSpan, tipo: str | None
    ) -> dict[str, object]:
        if len(call.args) > 4:
            self._stop(
                f"{call.name}: el lienzo admite hasta 4 argumentos.",
                span,
                "Parte la llamada en varios pasos.",
            )
        fields: dict[str, object] = {"NOMBRE": call.name}
        if tipo is not None:
            fields["TIPO"] = tipo
        inputs: dict[str, object] = {
            f"ARG{index}": _slot(self._expr(arg)) for index, arg in enumerate(call.args, start=1)
        }
        return self._block(kind, span, fields, inputs or None, {"argumentos": len(call.args)})

    def _function_block(self, function: FunctionDecl) -> dict[str, object]:
        if len(function.params) > 4:
            self._stop(
                "Funciones: el lienzo admite hasta 4 parámetros.",
                function.span,
                "Parte la función en pasos más chicos.",
            )
        fields: dict[str, object] = {"RESULTADO": function.result_name, "NOMBRE": function.name}
        for index, param in enumerate(function.params, start=1):
            fields[f"PARAM{index}"] = param.name
            fields[f"MODO{index}"] = "referencia" if param.mode == "reference" else "valor"
        inputs: dict[str, object] = {}
        self._body(inputs, "CUERPO", function.body)
        return self._block(
            "traza_funcion",
            function.span,
            fields,
            inputs or None,
            {"parametros": len(function.params)},
        )

    def _procedure_block(self, procedure: ProcedureDecl) -> dict[str, object]:
        if len(procedure.params) > 4:
            self._stop(
                "Procedimientos: el lienzo admite hasta 4 parámetros.",
                procedure.span,
                "Parte el procedimiento en pasos más chicos.",
            )
        fields: dict[str, object] = {"NOMBRE": procedure.name}
        for index, param in enumerate(procedure.params, start=1):
            fields[f"PARAM{index}"] = param.name
            fields[f"MODO{index}"] = "referencia" if param.mode == "reference" else "valor"
        inputs: dict[str, object] = {}
        self._body(inputs, "CUERPO", procedure.body)
        return self._block(
            "traza_procedimiento",
            procedure.span,
            fields,
            inputs or None,
            {"parametros": len(procedure.params)},
        )

    def _result_type(self, name: str, statements: tuple[Stmt, ...]) -> str:
        return self._find_type(name, statements) or "entero"

    def _find_type(self, name: str, statements: tuple[Stmt, ...]) -> str | None:
        for statement in statements:
            if isinstance(statement, DefineStmt) and name in statement.names:
                return statement.type_name
            nested = self._nested(statement)
            if nested:
                found = self._find_type(name, nested)
                if found is not None:
                    return found
        return None

    def _nested(self, statement: Stmt) -> tuple[Stmt, ...]:
        if isinstance(statement, IfStmt):
            return statement.then_body + (statement.else_body or ())
        if isinstance(statement, (WhileStmt, RepeatStmt, ForStmt)):
            return statement.body
        if isinstance(statement, SwitchStmt):
            rows = [item for case in statement.cases for item in case.body]
            if statement.default_body is not None:
                rows.extend(statement.default_body)
            return tuple(rows)
        return ()

    def _for(self, statement: ForStmt) -> dict[str, object]:
        step = statement.step if statement.step is not None else self._invented_step(statement)
        inputs: dict[str, object] = {
            "DESDE": _slot(self._expr(statement.start)),
            "HASTA": _slot(self._expr(statement.end)),
            "PASO": _slot(self._expr(step)),
        }
        self._body(inputs, "CUERPO", statement.body)
        return self._block("traza_para", statement.span, {"NOMBRE": statement.variable}, inputs)

    def _invented_step(self, statement: ForStmt) -> LiteralExpr:
        start = _const_int(statement.start)
        end = _const_int(statement.end)
        value = -1 if start is not None and end is not None and start > end else 1
        self.warnings.append(
            _error(
                self.source,
                f"Para: el archivo no traía paso. El bloque usa {value}.",
                statement.span,
                "Escribe Con Paso si el recorrido no es de uno en uno.",
                severity="warning",
                code="L0007",
            )
        )
        return LiteralExpr("entero", value, str(abs(value)), statement.span)

    def _switch(self, statement: SwitchStmt) -> dict[str, object]:
        expanded: list[tuple[Expr, tuple[Stmt, ...]]] = []
        for case in statement.cases:
            for label in case.labels:
                expanded.append((label, case.body))
        if not expanded:
            self._stop(
                "Segun: el lienzo necesita al menos un caso.",
                statement.span,
                "Agrega un caso antes de De Otro Modo.",
            )
        if len(expanded) > MAX_SEGUN_CASES:
            self._stop(
                "Segun: el lienzo admite hasta 12 casos.",
                statement.span,
                "Parte la opción múltiple en dos Segun.",
            )
        inputs: dict[str, object] = {"VALOR": _slot(self._expr(statement.selector))}
        for index, (label, body) in enumerate(expanded, start=1):
            inputs[f"CASO{index}"] = _slot(self._expr(label))
            self._body(inputs, f"HACER{index}", body)
        if statement.default_body:
            self._body(inputs, "OTRO", statement.default_body)
        return self._block(
            "traza_segun",
            statement.span,
            inputs=inputs,
            extra={"casos": len(expanded)},
        )

    def _body(self, inputs: dict[str, object], slot: str, statements: tuple[Stmt, ...]) -> None:
        top = self._sequence(statements)
        if top is not None:
            inputs[slot] = _slot(top)

    def _expr(self, expr: Expr) -> dict[str, object]:
        self._enter(
            expr.span, "La expresión es demasiado profunda.", "Divide la cuenta en varios pasos."
        )
        try:
            return self._expr_at(expr)
        finally:
            self.depth -= 1

    def _expr_at(self, expr: Expr) -> dict[str, object]:
        if isinstance(expr, UnaryExpr) and expr.operator == "pos":
            return self._expr_at(expr.operand)
        if isinstance(expr, UnaryExpr) and expr.operator == "neg":
            inner = expr.operand
            if isinstance(inner, LiteralExpr) and inner.kind in ("entero", "real"):
                return self._signed_literal(inner, negative=True)
            return self._binary("traza_aritmetica", "sub", self._zero_like(inner, expr.span), inner)
        if isinstance(expr, UnaryExpr) and expr.operator == "not":
            return self._block(
                "traza_no",
                expr.span,
                inputs={"VALOR": _slot(self._expr(expr.operand))},
            )
        if isinstance(expr, LiteralExpr):
            return self._signed_literal(expr, negative=False)
        if isinstance(expr, NameExpr):
            hinted = self.types.get(expr.name, "entero")
            return self._block(
                "traza_variable",
                expr.span,
                {"NOMBRE": expr.name, "TIPO": hinted},
            )
        if isinstance(expr, BinaryExpr):
            return self._binary_expr(expr)
        if isinstance(expr, CallExpr):
            if expr.name.casefold() == "concatenar" and len(expr.args) == 2:
                return self._block(
                    "traza_unir",
                    expr.span,
                    inputs={
                        "IZQUIERDA": _slot(self._expr(expr.args[0])),
                        "DERECHA": _slot(self._expr(expr.args[1])),
                    },
                )
            return self._call_block("traza_llamada", expr, expr.span, self._call_type(expr))
        if isinstance(expr, IndexExpr):
            return self._index_block(expr)
        self._stop(
            "El lienzo no tiene un bloque para esa expresión.",
            expr.span,
            "Usa los bloques de la caja.",
        )

    def _binary_expr(self, expr: BinaryExpr) -> dict[str, object]:
        if expr.operator in _ARITH:
            kind = "traza_aritmetica"
        elif expr.operator in _REL:
            kind = "traza_relacional"
        elif expr.operator in _LOGIC:
            kind = "traza_logica"
        elif expr.operator == "pow":
            self._stop(
                "Potencia: el lienzo no tiene el operador ^.",
                expr.span,
                "Calcula la potencia con multiplicaciones.",
            )
        else:
            self._stop(
                "El lienzo no tiene ese operador.",
                expr.span,
                "Usa los operadores de la caja.",
            )
        return self._binary(kind, expr.operator, expr.left, expr.right)

    def _binary(self, kind: str, operator: str, left: Expr, right: Expr) -> dict[str, object]:
        return self._block(
            kind,
            left.span,
            {"OPERADOR": operator},
            {"IZQUIERDA": _slot(self._expr(left)), "DERECHA": _slot(self._expr(right))},
        )

    def _signed_literal(self, expr: LiteralExpr, *, negative: bool) -> dict[str, object]:
        if expr.kind == "entero" and isinstance(expr.value, int):
            number = -abs(expr.value) if negative else expr.value
            return self._block("traza_entero", expr.span, {"VALOR": number})
        if expr.kind == "real" and isinstance(expr.value, Decimal):
            text = format_real(expr.value)
            if negative:
                text = f"-{text}"
            return self._block("traza_real", expr.span, {"VALOR": text})
        if expr.kind == "cadena" and isinstance(expr.value, str) and not negative:
            return self._block("traza_cadena", expr.span, {"VALOR": expr.value})
        if expr.kind == "caracter" and isinstance(expr.value, str) and not negative:
            return self._block("traza_caracter", expr.span, {"VALOR": expr.value})
        if expr.kind == "logico" and isinstance(expr.value, bool) and not negative:
            return self._block(
                "traza_logico",
                expr.span,
                {"VALOR": "verdadero" if expr.value else "falso"},
            )
        self._stop(
            "El lienzo no tiene un bloque para ese valor.", expr.span, "Usa un bloque de la caja."
        )

    def _zero_like(self, expr: Expr, span: SourceSpan) -> LiteralExpr:
        if isinstance(expr, NameExpr) and self.types.get(expr.name) == "real":
            return LiteralExpr("real", Decimal("0"), "0.0", span)
        if isinstance(expr, LiteralExpr) and expr.kind == "real":
            return LiteralExpr("real", Decimal("0"), "0.0", span)
        return LiteralExpr("entero", 0, "0", span)

    def _block(
        self,
        type_name: str,
        span: SourceSpan,
        fields: dict[str, object] | None = None,
        inputs: dict[str, object] | None = None,
        extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        self.ids += 1
        if self.ids > MAX_BLOCKS:
            self._stop(
                "Hay demasiados bloques.", span, "Parte el algoritmo en menos bloques.", "L0006"
            )
        data: dict[str, object] = {"type": type_name, "id": f"b{self.ids}"}
        if fields:
            data["fields"] = fields
        if inputs:
            data["inputs"] = inputs
        if extra:
            data["extraState"] = extra
        return data

    def _enter(self, span: SourceSpan, message: str, suggestion: str) -> None:
        self.depth += 1
        if self.depth > MAX_DEPTH:
            self._stop(message, span, suggestion, "L0006")

    def _reject(self, concept: str, span: SourceSpan) -> NoReturn:
        self._stop(
            f"{concept}: el lienzo no tiene ese bloque.",
            span,
            "El laboratorio todavía no arma arreglos.",
        )

    def _stop(
        self, message: str, span: SourceSpan, suggestion: str, code: str = "L0001"
    ) -> NoReturn:
        raise _Refuse(_error(self.source, message, span, suggestion, code=code))


def _slot(child: dict[str, object]) -> dict[str, object]:
    return {"block": child}


def _const_int(expr: Expr) -> int | None:
    if isinstance(expr, LiteralExpr) and expr.kind == "entero" and isinstance(expr.value, int):
        return expr.value
    if isinstance(expr, UnaryExpr) and expr.operator == "neg":
        inner = _const_int(expr.operand)
        if inner is not None:
            return -inner
    if isinstance(expr, UnaryExpr) and expr.operator == "pos":
        return _const_int(expr.operand)
    return None
