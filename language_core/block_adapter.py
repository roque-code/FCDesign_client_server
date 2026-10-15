"""JSON de Blockly al AST actual.

No ejecuta. Un bloque desconocido o una entrada vacía no produce programa.
Los errores de tipos sí dejan el árbol: los informa el analizador de siempre.
"""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Literal, NoReturn

from language_core.ast_nodes import (
    Algorithm,
    AssignStmt,
    BinaryExpr,
    CallExpr,
    CallStmt,
    ClearStmt,
    DefineStmt,
    DimDecl,
    DimensionStmt,
    Expr,
    ForStmt,
    FunctionDecl,
    IfStmt,
    IndexExpr,
    LiteralExpr,
    LValue,
    NameExpr,
    Param,
    ProcedureDecl,
    Program,
    ReadStmt,
    RepeatStmt,
    SourceSpan,
    Stmt,
    SwitchCase,
    SwitchStmt,
    TypeName,
    UnaryExpr,
    WaitStmt,
    WhileStmt,
    WriteStmt,
    merge_spans,
)
from language_core.diagnostics import Diagnostic, make_diagnostic
from language_core.dialect import resolve_keyword
from language_core.grammar import BP_NOT, BP_REL, BP_UNARY, STRICT, canonicalize
from language_core.lexer import MAX_NUMBER_DIGITS
from language_core.pseudocode import (
    BINARY_SYMBOL,
    PRIMARY,
    TYPE_LABEL,
    binary_power,
    format_real,
    needs_paren,
    quote_text,
)
from language_core.semantic_analyzer import analyze

MAX_BLOCKS = 400
MAX_DEPTH = 64
MAX_SEGUN_CASES = 12
MAX_DIMENSIONS = 4
MAX_PARAMETERS = 4
MAX_WRITE_VALUES = 8
ALGORITHM_NAME = "Laboratorio"

_STATEMENTS = frozenset(
    {
        "traza_definir",
        "traza_asignar",
        "traza_leer",
        "traza_escribir",
        "traza_borrar_pantalla",
        "traza_esperar",
        "traza_si",
        "traza_si_sino",
        "traza_mientras",
        "traza_segun",
        "traza_para",
        "traza_repetir",
        "traza_dimension",
        "traza_asignar_indice",
        "traza_leer_indice",
        "traza_llamar",
    }
)
_FIXED_BODIES = frozenset({"ENTONCES", "SINO", "CUERPO", "OTRO"})
_EXPRESSIONS = frozenset(
    {
        "traza_variable",
        "traza_entero",
        "traza_real",
        "traza_cadena",
        "traza_caracter",
        "traza_logico",
        "traza_aritmetica",
        "traza_relacional",
        "traza_logica",
        "traza_no",
        "traza_unir",
        "traza_indice",
        "traza_llamada",
    }
)

ArithOp = Literal["add", "sub", "mul", "div", "idiv", "mod"]
RelOp = Literal["eq", "neq", "lt", "lte", "gt", "gte"]
LogicOp = Literal["and", "or"]


class _Stop(Exception):
    """La estructura del workspace no se puede convertir."""


@dataclass(frozen=True)
class BlockBinding:
    """Dónde empieza el texto de un bloque. No vive dentro del AST."""

    block_id: str
    line: int
    column: int


@dataclass(frozen=True)
class Adapted:
    """Programa, vista en texto, vínculos y diagnósticos."""

    program: Program | None
    source: str
    bindings: tuple[BlockBinding, ...]
    diagnostics: tuple[Diagnostic, ...]


def adapt_workspace(data: object, *, algorithm_name: str = ALGORITHM_NAME) -> Adapted:
    """Convierte el JSON de `serialization.workspaces.save` en un programa."""
    if not _valid_name(algorithm_name):
        return _failed("L0003", "El nombre del algoritmo no es válido.", "Usa un identificador.")
    tops = _tops(data)
    if tops is None:
        return _failed("L0005", "No reconozco el workspace.", "Vuelve a armar el lienzo.")
    writer = _Writer(_declared_types(tops))
    try:
        program = writer.build(tops, algorithm_name)
    except _Stop:
        diagnostic = writer.diagnostic
        if diagnostic is None:
            return _failed("L0005", "No reconozco el workspace.", "Vuelve a armar el lienzo.")
        return Adapted(None, "", (), (diagnostic,))
    source = writer.source()
    notes = tuple(
        make_diagnostic(source, "warning", code, message, span, suggestion)
        for code, message, span, suggestion in writer.notes
    )
    return Adapted(
        program, source, tuple(writer.bindings), notes + analyze(program, STRICT, source)
    )


def _failed(code: str, message: str, suggestion: str) -> Adapted:
    span = SourceSpan(1, 1, 1, 1)
    return Adapted(None, "", (), (make_diagnostic("", "error", code, message, span, suggestion),))


class _Writer:
    """Emite el pseudocódigo y, a la vez, los nodos con su posición."""

    def __init__(self, declared: dict[str, TypeName]) -> None:
        self.declared = declared
        self.lines = [""]
        self.line = 1
        self.col = 1
        self.bindings: list[BlockBinding] = []
        self.notes: list[tuple[str, str, SourceSpan, str]] = []
        self.seen: set[str] = set()
        self.count = 0
        self.indent = 1
        self.diagnostic: Diagnostic | None = None

    def source(self) -> str:
        return "\n".join(self.lines) + "\n"

    def build(self, tops: list[dict[str, object]], algorithm_name: str) -> Program:
        functions: list[dict[str, object]] = []
        procedures: list[dict[str, object]] = []
        statements: list[dict[str, object]] = []
        for top in tops:
            kind = top.get("type")
            if kind in ("traza_funcion", "traza_procedimiento"):
                if _next(top) is not None:
                    self._fail(
                        "L0004",
                        "Una función o un procedimiento no se engancha a otra sentencia.",
                        "Suéltalo solo en el lienzo.",
                    )
                if kind == "traza_funcion":
                    functions.append(top)
                else:
                    procedures.append(top)
            else:
                statements.append(top)
        saved = self.indent
        self.indent = 0
        function_nodes = [self._funcion(block) for block in functions]
        procedure_nodes = [self._procedimiento(block) for block in procedures]
        self.indent = saved
        header = self._write("Algoritmo ")
        name_span = self._write(algorithm_name)
        self._newline()
        body: list[Stmt] = []
        for top in statements:
            block: dict[str, object] | None = top
            while block is not None:
                self._write(self._pad())
                body.append(self._statement(block))
                self._newline()
                block = _next(block)
        footer = self._write("FinAlgoritmo")
        span = merge_spans(header, footer)
        if function_nodes:
            span = merge_spans(function_nodes[0].span, footer)
        elif procedure_nodes:
            span = merge_spans(procedure_nodes[0].span, footer)
        return Program(
            Algorithm(algorithm_name, name_span, tuple(body), span),
            tuple(function_nodes),
            tuple(procedure_nodes),
            span,
        )

    def _statement(self, block: dict[str, object]) -> Stmt:
        ident = self._claim(block)
        self._bind(ident)
        origin = self._here()
        kind = block.get("type")
        if kind == "traza_definir":
            statement: Stmt = self._definir(block)
        elif kind == "traza_asignar":
            statement = self._asignar(block)
        elif kind == "traza_leer":
            statement = self._leer(block)
        elif kind == "traza_escribir":
            statement = self._escribir(block)
        elif kind == "traza_borrar_pantalla":
            statement = self._borrar(block)
        elif kind == "traza_esperar":
            statement = self._esperar(block)
        elif kind == "traza_si":
            return self._si(block, origin, with_else=False)
        elif kind == "traza_si_sino":
            return self._si(block, origin, with_else=True)
        elif kind == "traza_mientras":
            return self._mientras(block, origin)
        elif kind == "traza_segun":
            return self._segun(block, origin)
        elif kind == "traza_para":
            return self._para(block, origin)
        elif kind == "traza_repetir":
            return self._repetir(block, origin)
        elif kind == "traza_dimension":
            statement = self._dimension(block)
        elif kind == "traza_asignar_indice":
            statement = self._asignar_indice(block)
        elif kind == "traza_leer_indice":
            statement = self._leer_indice(block)
        elif kind == "traza_llamar":
            statement = self._llamar(block)
        elif kind in ("traza_funcion", "traza_procedimiento"):
            self._fail(
                "L0004",
                "Una función o un procedimiento va aparte del algoritmo.",
                "Suéltalo en el lienzo, sin engancharlo a otra sentencia.",
            )
        elif isinstance(kind, str) and kind in _EXPRESSIONS:
            self._fail(
                "L0004",
                "Este bloque tiene que ir dentro de una sentencia.",
                "Conéctalo a una sentencia, no a una entrada de valor.",
            )
        else:
            self._fail("L0001", _unknown(kind), "Usa los bloques de la caja.")
        end = self._write(";")
        return replace(statement, span=merge_spans(origin, end))

    def _si(self, block: dict[str, object], origin: SourceSpan, *, with_else: bool) -> IfStmt:
        self._write("Si ")
        condition = self._expr(self._required(block, "CONDICION"), 0, "left", 1)
        self._write(" Entonces")
        then_body = self._body(block, "ENTONCES")
        else_body: tuple[Stmt, ...] | None = None
        if with_else:
            self._newline()
            self._write(self._pad())
            self._write("Sino")
            else_body = self._body(block, "SINO")
        self._newline()
        self._write(self._pad())
        end = self._write("FinSi")
        return IfStmt(condition, then_body, else_body, merge_spans(origin, end))

    def _mientras(self, block: dict[str, object], origin: SourceSpan) -> WhileStmt:
        self._write("Mientras ")
        condition = self._expr(self._required(block, "CONDICION"), 0, "left", 1)
        self._write(" Hacer")
        body = self._body(block, "CUERPO")
        self._newline()
        self._write(self._pad())
        end = self._write("FinMientras")
        return WhileStmt(condition, body, merge_spans(origin, end))

    def _segun(self, block: dict[str, object], origin: SourceSpan) -> SwitchStmt:
        self._write("Segun ")
        selector = self._expr(self._required(block, "VALOR"), 0, "left", 1)
        self._write(" Hacer")
        cases: list[SwitchCase] = []
        for index in range(1, _segun_count(block) + 1):
            self.indent += 1
            self._newline()
            self._write(self._pad())
            label = self._expr(self._required(block, f"CASO{index}"), 0, "left", 1)
            colon = self._write(":")
            body = self._body(block, f"HACER{index}")
            self.indent -= 1
            cases.append(SwitchCase((label,), body, merge_spans(label.span, colon)))
        self.indent += 1
        self._newline()
        self._write(self._pad())
        self._write("De Otro Modo:")
        default_body = self._body(block, "OTRO")
        self.indent -= 1
        self._newline()
        self._write(self._pad())
        end = self._write("FinSegun")
        return SwitchStmt(selector, tuple(cases), default_body, merge_spans(origin, end))

    def _para(self, block: dict[str, object], origin: SourceSpan) -> ForStmt:
        self._write("Para ")
        name = self._name(block)
        name_span = self._write(name)
        self._write(" <- ")
        start = self._expr(self._required(block, "DESDE"), 0, "left", 1)
        self._write(" Hasta ")
        end = self._expr(self._required(block, "HASTA"), 0, "left", 1)
        self._write(" Con Paso ")
        step = self._expr(self._required(block, "PASO"), 0, "left", 1)
        self._write(" Hacer")
        body = self._body(block, "CUERPO")
        self._newline()
        self._write(self._pad())
        closer = self._write("FinPara")
        return ForStmt(name, name_span, start, end, step, body, merge_spans(origin, closer))

    def _repetir(self, block: dict[str, object], origin: SourceSpan) -> RepeatStmt:
        self._write("Repetir")
        body = self._body(block, "CUERPO")
        self._newline()
        self._write(self._pad())
        self._write("Hasta Que ")
        condition = self._expr(self._required(block, "CONDICION"), 0, "left", 1)
        return RepeatStmt(body, condition, merge_spans(origin, condition.span))

    def _funcion(self, block: dict[str, object]) -> FunctionDecl:
        self._bind(self._claim(block))
        origin = self._write("Funcion ")
        result = self._named(block, "RESULTADO")
        self._write(f"{result} <- ")
        name = self._named(block, "NOMBRE")
        self._write(f"{name}(")
        params = self._param_list(block)
        self._write(")")
        body = self._body(block, "CUERPO")
        self._newline()
        end = self._write("FinFuncion")
        self._newline()
        return FunctionDecl(result, name, params, body, merge_spans(origin, end))

    def _procedimiento(self, block: dict[str, object]) -> ProcedureDecl:
        self._bind(self._claim(block))
        origin = self._write("SubProceso ")
        name = self._named(block, "NOMBRE")
        self._write(f"{name}(")
        params = self._param_list(block)
        self._write(")")
        body = self._body(block, "CUERPO")
        self._newline()
        end = self._write("FinSubProceso")
        self._newline()
        return ProcedureDecl(name, params, body, merge_spans(origin, end))

    def _param_list(self, block: dict[str, object]) -> tuple[Param, ...]:
        count = _counted(block, "parametros", "PARAM", 1, 0, MAX_PARAMETERS)
        params: list[Param] = []
        for index in range(1, count + 1):
            if index > 1:
                self._write(", ")
            name = self._named(block, f"PARAM{index}")
            span = self._write(name)
            mode = _field(block, f"MODO{index}")
            if mode in (None, "valor"):
                params.append(Param(name, "value", span))
            elif mode == "referencia":
                self._write(" Por Referencia")
                params.append(Param(name, "reference", span, True))
            else:
                self._fail(
                    "L0002",
                    "El modo del parámetro no es válido.",
                    "Elige por valor o por referencia.",
                )
        return tuple(params)

    def _dimension(self, block: dict[str, object]) -> DimensionStmt:
        name = self._name(block)
        type_name = self._type_name(block)
        self._write(f"Dimension {name}[")
        lengths = self._slots(block, "TAMANO", "dimensiones", 1, 1, MAX_DIMENSIONS)
        end = self._write(f"] Como {TYPE_LABEL[type_name]}")
        decl = DimDecl(name, tuple(lengths), type_name, merge_spans(lengths[0].span, end))
        return DimensionStmt((decl,), decl.span)

    def _asignar_indice(self, block: dict[str, object]) -> AssignStmt:
        name = self._name(block)
        name_span = self._write(f"{name}[")
        indexes = self._slots(block, "INDICE", "dimensiones", 1, 1, MAX_DIMENSIONS)
        self._write("] <- ")
        value = self._expr(self._required(block, "VALOR"), 0, "left", 1)
        target = LValue(name, tuple(indexes), name_span)
        return AssignStmt(target, value, merge_spans(name_span, value.span))

    def _leer_indice(self, block: dict[str, object]) -> ReadStmt:
        name = self._name(block)
        self._write("Leer ")
        name_span = self._write(f"{name}[")
        indexes = self._slots(block, "INDICE", "dimensiones", 1, 1, MAX_DIMENSIONS)
        end = self._write("]")
        target = LValue(name, tuple(indexes), merge_spans(name_span, end))
        return ReadStmt((target,), target.span)

    def _llamar(self, block: dict[str, object]) -> CallStmt:
        call = self._call(block, 1)
        return CallStmt(call, call.span)

    def _indice(self, block: dict[str, object], depth: int) -> IndexExpr:
        name = self._name(block)
        hinted = _as_type(_field(block, "TIPO"))
        declared = self.declared.get(name)
        span = self._write(f"{name}[")
        if hinted is not None and declared is not None and hinted != declared:
            self.notes.append(
                (
                    "L0101",
                    (
                        f"El bloque de {name} dice {TYPE_LABEL[hinted]}, "
                        f"pero está definido como {TYPE_LABEL[declared]}."
                    ),
                    span,
                    "El tipo lo fija Definir. El menú del bloque solo limita las conexiones.",
                )
            )
        indexes = self._slots(block, "INDICE", "dimensiones", 1, 1, MAX_DIMENSIONS, depth)
        end = self._write("]")
        return IndexExpr(name, tuple(indexes), merge_spans(span, end))

    def _llamada(self, block: dict[str, object], depth: int) -> CallExpr:
        return self._call(block, depth)

    def _call(self, block: dict[str, object], depth: int) -> CallExpr:
        name = self._named(block, "NOMBRE")
        start = self._write(f"{name}(")
        count = _counted(block, "argumentos", "ARG", 1, 0, MAX_PARAMETERS)
        args: list[Expr] = []
        for index in range(1, count + 1):
            if index > 1:
                self._write(", ")
            args.append(self._expr(self._required(block, f"ARG{index}"), 0, "left", depth + 1))
        end = self._write(")")
        return CallExpr(name, tuple(args), merge_spans(start, end))

    def _slots(
        self,
        block: dict[str, object],
        prefix: str,
        key: str,
        default: int,
        low: int,
        high: int,
        depth: int = 1,
    ) -> list[Expr]:
        count = _counted(block, key, prefix, default, low, high)
        if count < 1:
            self._fail("L0002", "Falta un valor en el bloque.", "Completa la entrada vacía.")
        values: list[Expr] = []
        for index in range(1, count + 1):
            if index > 1:
                self._write(", ")
            values.append(
                self._expr(self._required(block, f"{prefix}{index}"), 0, "left", depth + 1)
            )
        return values

    def _named(self, block: dict[str, object], field: str) -> str:
        raw = _field(block, field)
        if not isinstance(raw, str) or not _valid_name(raw):
            self._fail(
                "L0003",
                "El nombre no es válido.",
                "Usa letras y no una palabra del lenguaje.",
            )
        return raw

    def _body(self, block: dict[str, object], slot: str) -> tuple[Stmt, ...]:
        if self.indent >= MAX_DEPTH:
            self._fail(
                "L0006",
                "Hay demasiados bloques anidados.",
                "Saca un Si o un Mientras afuera.",
            )
        self.indent += 1
        try:
            statements: list[Stmt] = []
            child = _child(block, slot)
            while child is not None:
                self._newline()
                self._write(self._pad())
                statements.append(self._statement(child))
                child = _next(child)
            return tuple(statements)
        finally:
            self.indent -= 1

    def _pad(self) -> str:
        return "    " * self.indent

    def _definir(self, block: dict[str, object]) -> DefineStmt:
        name = self._name(block)
        type_name = self._type_name(block)
        self._write("Definir ")
        name_span = self._write(name)
        self._write(f" Como {TYPE_LABEL[type_name]}")
        return DefineStmt((name,), (name_span,), type_name, name_span)

    def _asignar(self, block: dict[str, object]) -> AssignStmt:
        name = self._name(block)
        name_span = self._write(name)
        self._write(" <- ")
        value = self._expr(self._required(block, "VALOR"), 0, "left", 1)
        return AssignStmt(LValue(name, (), name_span), value, merge_spans(name_span, value.span))

    def _leer(self, block: dict[str, object]) -> ReadStmt:
        name = self._name(block)
        self._write("Leer ")
        name_span = self._write(name)
        return ReadStmt((LValue(name, (), name_span),), name_span)

    def _escribir(self, block: dict[str, object]) -> WriteStmt:
        count = _counted(block, "valores", "VALOR", 1, 1, MAX_WRITE_VALUES)
        self._write("Escribir ")
        values = [self._expr(self._required(block, "VALOR"), 0, "left", 1)]
        for index in range(2, count + 1):
            self._write(", ")
            values.append(self._expr(self._required(block, f"VALOR{index}"), 0, "left", 1))
        stay = _checked(block, "SIN_SALTAR")
        if stay:
            self._write(" Sin Saltar")
        return WriteStmt(tuple(values), values[0].span, newline=not stay)

    def _borrar(self, block: dict[str, object]) -> ClearStmt:
        span = self._write("Borrar Pantalla")
        return ClearStmt(span)

    def _esperar(self, block: dict[str, object]) -> WaitStmt:
        self._write("Esperar ")
        seconds = self._expr(self._required(block, "SEGUNDOS"), 0, "left", 1)
        self._write(" Segundos")
        return WaitStmt(seconds, seconds.span)

    def _expr(self, block: dict[str, object], parent_bp: int, side: str, depth: int) -> Expr:
        if depth > MAX_DEPTH:
            self._fail(
                "L0006",
                "La expresión es demasiado profunda.",
                "Divide la cuenta en varios pasos.",
            )
        ident = self._claim(block)
        kind = block.get("type")
        if not isinstance(kind, str) or kind not in _EXPRESSIONS:
            if isinstance(kind, str) and kind in _STATEMENTS:
                self._fail(
                    "L0004",
                    "Una sentencia no puede usarse como valor.",
                    "Ese bloque va en el lienzo, no dentro de una entrada.",
                )
            self._fail("L0001", _unknown(kind), "Usa los bloques de la caja.")
        power, assoc = _json_power(block)
        self._bind(ident)
        if needs_paren(power, assoc, parent_bp, side):
            start = self._write("(")
            expr = self._expr_body(block, kind, depth)
            end = self._write(")")
            return replace(expr, span=merge_spans(start, end))
        return self._expr_body(block, kind, depth)

    def _expr_body(self, block: dict[str, object], kind: str, depth: int) -> Expr:
        if kind == "traza_variable":
            return self._variable(block)
        if kind == "traza_entero":
            return self._number(block, "entero")
        if kind == "traza_real":
            return self._number(block, "real")
        if kind == "traza_cadena":
            return self._text(block)
        if kind == "traza_caracter":
            return self._character(block)
        if kind == "traza_logico":
            return self._logic_literal(block)
        if kind == "traza_aritmetica":
            return self._arithmetic(block, depth)
        if kind == "traza_relacional":
            return self._relation(block, depth)
        if kind == "traza_logica":
            return self._logic(block, depth)
        if kind == "traza_no":
            return self._not(block, depth)
        if kind == "traza_unir":
            return self._join(block, depth)
        if kind == "traza_indice":
            return self._indice(block, depth)
        if kind == "traza_llamada":
            return self._llamada(block, depth)
        self._fail("L0001", _unknown(kind), "Usa los bloques de la caja.")

    def _variable(self, block: dict[str, object]) -> NameExpr:
        name = self._name(block)
        hinted = _as_type(_field(block, "TIPO"))
        declared = self.declared.get(name)
        span = self._write(name)
        if hinted is not None and declared is not None and hinted != declared:
            self.notes.append(
                (
                    "L0101",
                    (
                        f"El bloque de {name} dice {TYPE_LABEL[hinted]}, "
                        f"pero está definido como {TYPE_LABEL[declared]}."
                    ),
                    span,
                    "El tipo lo fija Definir. El menú del bloque solo limita las conexiones.",
                )
            )
        return NameExpr(name, span)

    def _number(self, block: dict[str, object], kind: TypeName) -> Expr:
        number = _decimal(_field(block, "VALOR"))
        if number is None:
            self._fail("L0002", "El número no es válido.", "Escribe un número finito.")
        if kind == "entero" and number != number.to_integral_value():
            self._fail(
                "L0002",
                "El entero no puede tener parte decimal.",
                "Usa el bloque de número real.",
            )
        negative = number < 0
        if kind == "entero":
            text = str(int(abs(number)))
            if len(text) > MAX_NUMBER_DIGITS:
                self._fail("L0002", "El número es demasiado largo.", "Usa un entero más corto.")
            if negative:
                sign = self._write("-")
                literal = LiteralExpr("entero", int(text), text, self._write(text))
                return UnaryExpr("neg", literal, merge_spans(sign, literal.span))
            return LiteralExpr("entero", int(text), text, self._write(text))
        text = format_real(abs(number))
        if len(text) > MAX_NUMBER_DIGITS:
            self._fail("L0002", "El número es demasiado largo.", "Usa un real más corto.")
        if negative:
            sign = self._write("-")
            literal = LiteralExpr("real", Decimal(text), text, self._write(text))
            return UnaryExpr("neg", literal, merge_spans(sign, literal.span))
        return LiteralExpr("real", Decimal(text), text, self._write(text))

    def _text(self, block: dict[str, object]) -> LiteralExpr:
        raw = _field(block, "VALOR")
        if raw is None:
            raw = ""
        if not isinstance(raw, str):
            self._fail("L0002", "El texto no es válido.", "Escribe el texto en el bloque.")
        try:
            lexeme = quote_text(raw, '"')
        except ValueError:
            self._fail(
                "L0002",
                "El texto tiene un carácter que no se puede escribir.",
                "Quita los caracteres de control.",
            )
        return LiteralExpr("cadena", raw, lexeme, self._write(lexeme))

    def _character(self, block: dict[str, object]) -> LiteralExpr:
        raw = _field(block, "VALOR")
        if not isinstance(raw, str) or len(raw) != 1:
            self._fail(
                "L0002",
                "El carácter debe ser un solo símbolo.",
                "Si el texto es más largo, usa el bloque de cadena.",
            )
        try:
            lexeme = quote_text(raw, "'")
        except ValueError:
            self._fail(
                "L0002",
                "Ese carácter no se puede escribir.",
                "Elige una letra, un dígito o un signo visible.",
            )
        return LiteralExpr("caracter", raw, lexeme, self._write(lexeme))

    def _logic_literal(self, block: dict[str, object]) -> LiteralExpr:
        raw = _field(block, "VALOR")
        folded = canonicalize(raw) if isinstance(raw, str) else ""
        if folded == "verdadero":
            text, value = "Verdadero", True
        elif folded == "falso":
            text, value = "Falso", False
        else:
            self._fail("L0002", "El lógico debe ser Verdadero o Falso.", "Elige uno de los dos.")
        return LiteralExpr("logico", value, text, self._write(text))

    def _arithmetic(self, block: dict[str, object], depth: int) -> BinaryExpr:
        operator = _arith(_field(block, "OPERADOR"))
        if operator is None:
            self._fail(
                "L0002", "El operador aritmético no es válido.", "Elige +, -, *, /, DIV o MOD."
            )
        power, _assoc = binary_power(operator)
        left, right = self._sides(block, BINARY_SYMBOL[operator], power, depth)
        return BinaryExpr(operator, left, right, merge_spans(left.span, right.span))

    def _relation(self, block: dict[str, object], depth: int) -> BinaryExpr:
        operator = _relation_op(_field(block, "OPERADOR"))
        if operator is None:
            self._fail(
                "L0002",
                "El operador de comparación no es válido.",
                "Elige =, <>, <, <=, > o >=.",
            )
        left_block = _child(block, "IZQUIERDA")
        if left_block is not None and left_block.get("type") == "traza_relacional":
            self._fail(
                "L0004",
                "No se pueden encadenar comparaciones.",
                "Une las comparaciones con Y. Por ejemplo: a < b Y b < c.",
            )
        left, right = self._sides(block, BINARY_SYMBOL[operator], binary_power(operator)[0], depth)
        return BinaryExpr(operator, left, right, merge_spans(left.span, right.span))

    def _logic(self, block: dict[str, object], depth: int) -> BinaryExpr:
        operator = _logic_op(_field(block, "OPERADOR"))
        if operator is None:
            self._fail("L0002", "El operador lógico no es válido.", "Elige Y u O.")
        left, right = self._sides(block, BINARY_SYMBOL[operator], binary_power(operator)[0], depth)
        return BinaryExpr(operator, left, right, merge_spans(left.span, right.span))

    def _sides(
        self, block: dict[str, object], symbol: str, power: int, depth: int
    ) -> tuple[Expr, Expr]:
        left = self._expr(self._required(block, "IZQUIERDA"), power, "left", depth + 1)
        self._write(f" {symbol} ")
        right = self._expr(self._required(block, "DERECHA"), power, "right", depth + 1)
        return left, right

    def _not(self, block: dict[str, object], depth: int) -> UnaryExpr:
        start = self._write("NO ")
        operand = self._expr(self._required(block, "VALOR"), BP_NOT, "right", depth + 1)
        return UnaryExpr("not", operand, merge_spans(start, operand.span))

    def _join(self, block: dict[str, object], depth: int) -> CallExpr:
        start = self._write("Concatenar(")
        left = self._expr(self._required(block, "IZQUIERDA"), 0, "left", depth + 1)
        self._write(", ")
        right = self._expr(self._required(block, "DERECHA"), 0, "left", depth + 1)
        end = self._write(")")
        return CallExpr("Concatenar", (left, right), merge_spans(start, end))

    def _required(self, block: dict[str, object], slot: str) -> dict[str, object]:
        child = _child(block, slot)
        if child is None:
            self._fail("L0002", "Falta un valor en el bloque.", "Completa la entrada vacía.")
        return child

    def _name(self, block: dict[str, object]) -> str:
        raw = _field(block, "NOMBRE")
        if not isinstance(raw, str) or not _valid_name(raw):
            self._fail(
                "L0003",
                "El nombre de la variable no es válido.",
                "Usa letras y no una palabra del lenguaje.",
            )
        return raw

    def _type_name(self, block: dict[str, object]) -> TypeName:
        found = _as_type(_field(block, "TIPO"))
        if found is None:
            self._fail(
                "L0002",
                "El tipo no es válido.",
                "Elige Entero, Real, Lógico, Caracter o Cadena.",
            )
        return found

    def _claim(self, block: dict[str, object]) -> str:
        self.count += 1
        if self.count > MAX_BLOCKS:
            self._fail("L0006", "Hay demasiados bloques.", "Parte el algoritmo en menos bloques.")
        ident = block.get("id")
        if not isinstance(ident, str) or not ident:
            self._fail(
                "L0002", "A un bloque le falta el identificador.", "Vuelve a colocar el bloque."
            )
        if ident in self.seen:
            self._fail(
                "L0006",
                "Hay un bloque repetido en el workspace.",
                "Cada bloque debe aparecer una vez.",
            )
        self.seen.add(ident)
        return ident

    def _bind(self, block_id: str) -> None:
        self.bindings.append(BlockBinding(block_id, self.line, self.col))

    def _write(self, text: str) -> SourceSpan:
        span = SourceSpan(self.line, self.col, self.line, self.col + len(text) - 1)
        self.lines[-1] += text
        self.col += len(text)
        return span

    def _newline(self) -> None:
        self.lines.append("")
        self.line += 1
        self.col = 1

    def _here(self) -> SourceSpan:
        return SourceSpan(self.line, self.col, self.line, self.col)

    def _fail(self, code: str, message: str, suggestion: str) -> NoReturn:
        self.diagnostic = make_diagnostic("", "error", code, message, self._here(), suggestion)
        raise _Stop


def _json_power(block: dict[str, object]) -> tuple[int, str]:
    kind = block.get("type")
    if kind in ("traza_entero", "traza_real"):
        number = _decimal(_field(block, "VALOR"))
        if number is not None and number < 0:
            return BP_UNARY, "prefix"
        return PRIMARY, "primary"
    if kind == "traza_no":
        return BP_NOT, "prefix"
    if kind == "traza_aritmetica":
        arithmetic = _arith(_field(block, "OPERADOR"))
        if arithmetic is None:
            return PRIMARY, "primary"
        return binary_power(arithmetic)
    if kind == "traza_relacional":
        return BP_REL, "none"
    if kind == "traza_logica":
        logic = _logic_op(_field(block, "OPERADOR"))
        if logic is None:
            return PRIMARY, "primary"
        return binary_power(logic)
    return PRIMARY, "primary"


def _arith(value: object) -> ArithOp | None:
    if value == "add":
        return "add"
    if value == "sub":
        return "sub"
    if value == "mul":
        return "mul"
    if value == "div":
        return "div"
    if value == "idiv":
        return "idiv"
    if value == "mod":
        return "mod"
    return None


def _relation_op(value: object) -> RelOp | None:
    if value == "eq":
        return "eq"
    if value == "neq":
        return "neq"
    if value == "lt":
        return "lt"
    if value == "lte":
        return "lte"
    if value == "gt":
        return "gt"
    if value == "gte":
        return "gte"
    return None


def _logic_op(value: object) -> LogicOp | None:
    if value == "and":
        return "and"
    if value == "or":
        return "or"
    return None


def _as_type(value: object) -> TypeName | None:
    if value == "entero":
        return "entero"
    if value == "real":
        return "real"
    if value == "logico":
        return "logico"
    if value == "caracter":
        return "caracter"
    if value == "cadena":
        return "cadena"
    return None


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    number: Decimal | None = None
    if isinstance(value, int):
        number = Decimal(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            return None
        number = Decimal(str(value))
    elif isinstance(value, str):
        try:
            number = Decimal(value.strip())
        except InvalidOperation:
            return None
    if number is None or not number.is_finite():
        return None
    return number


def _valid_name(name: str) -> bool:
    if not name or resolve_keyword(canonicalize(name)) is not None:
        return False
    first = name[0]
    if first != "_" and not unicodedata.category(first).startswith("L"):
        return False
    for ch in name[1:]:
        if ch == "_":
            continue
        category = unicodedata.category(ch)
        if not (category.startswith("L") or category == "Nd"):
            return False
    return True


def _unknown(kind: object) -> str:
    if isinstance(kind, str) and kind and len(kind) <= 40:
        return f"No conozco el bloque {kind}."
    return "No conozco este bloque."


def _as_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    parsed: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        parsed[key] = item
    return parsed


def _checked(block: dict[str, object], name: str) -> bool:
    raw = _field(block, name)
    return raw is True or (isinstance(raw, str) and raw.upper() == "TRUE")


def _field(block: dict[str, object], name: str) -> object:
    fields = _as_dict(block.get("fields"))
    if fields is None:
        return None
    return fields.get(name)


def _counted(
    block: dict[str, object], key: str, prefix: str, default: int, low: int, high: int
) -> int:
    extra = block.get("extraState")
    if isinstance(extra, dict):
        raw = extra.get(key)
        if isinstance(raw, int) and not isinstance(raw, bool):
            return min(high, max(low, raw))
    fields = _as_dict(block.get("fields")) or {}
    inputs = _as_dict(block.get("inputs")) or {}
    found: list[int] = []
    for name in (*fields, *inputs):
        if not name.startswith(prefix):
            continue
        suffix = name[len(prefix) :]
        if suffix.isdigit():
            found.append(int(suffix))
    if not found:
        return default
    return min(high, max(low, max(found)))


def _segun_count(block: dict[str, object]) -> int:
    extra = block.get("extraState")
    if isinstance(extra, dict):
        raw = extra.get("casos")
        if isinstance(raw, int) and not isinstance(raw, bool):
            return min(MAX_SEGUN_CASES, max(1, raw))
    inputs = _as_dict(block.get("inputs")) or {}
    found = [_caso_index(key) for key in inputs]
    indexes = [index for index in found if index is not None]
    if not indexes:
        return 1
    return min(MAX_SEGUN_CASES, max(indexes))


def _caso_index(slot: str) -> int | None:
    if not slot.startswith("CASO"):
        return None
    suffix = slot[4:]
    if not suffix.isdigit():
        return None
    return int(suffix)


def _statement_slots(block: dict[str, object]) -> list[str]:
    inputs = _as_dict(block.get("inputs"))
    if inputs is None:
        return []
    return [slot for slot in inputs if slot in _FIXED_BODIES or _hacer_index(slot) is not None]


def _hacer_index(slot: str) -> int | None:
    if not slot.startswith("HACER"):
        return None
    suffix = slot[5:]
    if not suffix.isdigit():
        return None
    return int(suffix)


def _child(block: dict[str, object], slot: str) -> dict[str, object] | None:
    inputs = _as_dict(block.get("inputs"))
    if inputs is None:
        return None
    pocket = _as_dict(inputs.get(slot))
    if pocket is None:
        return None
    return _as_dict(pocket.get("block"))


def _next(block: dict[str, object]) -> dict[str, object] | None:
    pocket = _as_dict(block.get("next"))
    if pocket is None:
        return None
    return _as_dict(pocket.get("block"))


def _tops(data: object) -> list[dict[str, object]] | None:
    root = _as_dict(data)
    if root is None:
        return None
    # Un lienzo vacío no incluye la clave, o la guarda en null.
    if "blocks" not in root or root.get("blocks") is None:
        return []
    container = _as_dict(root.get("blocks"))
    raw = container.get("blocks") if container is not None else root.get("blocks")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return None
    tops: list[dict[str, object]] = []
    for item in raw:
        parsed = _as_dict(item)
        if parsed is None:
            return None
        tops.append(parsed)
    return tops


def _declared_types(tops: list[dict[str, object]]) -> dict[str, TypeName]:
    found: dict[str, TypeName] = {}
    for block in _each_block(tops):
        if block.get("type") not in ("traza_definir", "traza_dimension"):
            continue
        name = _field(block, "NOMBRE")
        kind = _as_type(_field(block, "TIPO"))
        if isinstance(name, str) and kind is not None and name not in found:
            found[name] = kind
    return found


def _each_block(tops: list[dict[str, object]]) -> Iterator[dict[str, object]]:
    pending = list(tops)
    seen = 0
    while pending and seen <= MAX_BLOCKS:
        block = pending.pop()
        seen += 1
        yield block
        nxt = _next(block)
        if nxt is not None:
            pending.append(nxt)
        for slot in _statement_slots(block):
            child = _child(block, slot)
            if child is not None:
                pending.append(child)
