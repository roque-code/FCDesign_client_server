"""Grafo de diagrama a partir del AST. No calcula coordenadas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from language_core.ast_nodes import (
    AssignStmt,
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

FlowKind = Literal["terminal", "process", "io", "decision", "subprocess", "join"]

_TYPES = {
    "entero": "Entero",
    "real": "Real",
    "logico": "Lógico",
    "caracter": "Caracter",
    "cadena": "Cadena",
}
_ATOM = 100
_BINARY: dict[str, tuple[str, int, str]] = {
    "or": ("O", 20, "left"),
    "and": ("Y", 30, "left"),
    "eq": ("==", 50, "none"),
    "neq": ("<>", 50, "none"),
    "lt": ("<", 50, "none"),
    "lte": ("<=", 50, "none"),
    "gt": (">", 50, "none"),
    "gte": (">=", 50, "none"),
    "add": ("+", 60, "left"),
    "sub": ("-", 60, "left"),
    "mul": ("*", 70, "left"),
    "div": ("/", 70, "left"),
    "idiv": ("DIV", 70, "left"),
    "mod": ("MOD", 70, "left"),
    "pow": ("^", 90, "right"),
}


@dataclass(frozen=True)
class FlowNode:
    id: str
    kind: FlowKind
    text: str
    span: SourceSpan | None
    figure: str = ""

    def as_dict(self) -> dict[str, object]:
        span = self.span
        return {
            "id": self.id,
            "kind": self.kind,
            "figure": self.figure or self.kind,
            "text": self.text,
            "line": None if span is None else span.start_line,
            "column": None if span is None else span.start_col,
            "end_line": None if span is None else span.end_line,
            "end_column": None if span is None else span.end_col,
        }


@dataclass(frozen=True)
class FlowEdge:
    source: str
    target: str
    label: str | None

    def as_dict(self) -> dict[str, object]:
        return {"source": self.source, "target": self.target, "label": self.label}


@dataclass(frozen=True)
class FlowGraph:
    nodes: tuple[FlowNode, ...]
    edges: tuple[FlowEdge, ...]
    entry: str

    def as_dict(self) -> dict[str, object]:
        return {
            "entry": self.entry,
            "nodes": [node.as_dict() for node in self.nodes],
            "edges": [edge.as_dict() for edge in self.edges],
        }


def build(program: Program) -> FlowGraph:
    """Recorre el algoritmo y cada subrutina. El ingreso es el inicio del algoritmo."""
    builder = _Builder()
    entry = builder.scope("Inicio", "Fin", program.algorithm.body, program.algorithm.span)
    for function in program.functions:
        _routine(builder, function)
    for procedure in program.procedures:
        _routine(builder, procedure)
    return FlowGraph(tuple(builder.nodes), tuple(builder.edges), entry)


def _routine(builder: _Builder, routine: FunctionDecl | ProcedureDecl) -> None:
    builder.scope(f"Inicio {routine.name}", f"Fin {routine.name}", routine.body, routine.span)


class _Builder:
    def __init__(self) -> None:
        self.nodes: list[FlowNode] = []
        self.edges: list[FlowEdge] = []
        self._count = 0

    def scope(
        self, start_text: str, end_text: str, body: tuple[Stmt, ...], span: SourceSpan
    ) -> str:
        start = self._node("terminal", start_text, span)
        if body:
            exit_id, exit_label = self._block(start, body, None)
        else:
            exit_id, exit_label = start, None
        end = self._node("terminal", end_text, span)
        self._edge(exit_id, end, exit_label)
        return start

    def _node(
        self, kind: FlowKind, text: str, span: SourceSpan | None, figure: str | None = None
    ) -> str:
        self._count += 1
        ident = f"n{self._count}"
        self.nodes.append(FlowNode(ident, kind, text, span, figure or kind))
        return ident

    def _edge(self, source: str, target: str, label: str | None) -> None:
        self.edges.append(FlowEdge(source, target, label))

    def _block(
        self, incoming: str, body: tuple[Stmt, ...], label: str | None
    ) -> tuple[str, str | None]:
        cursor = incoming
        pending = label
        for statement in body:
            cursor, pending = self._statement(cursor, statement, pending)
        return cursor, pending

    def _finish(self, origin: str, body: tuple[Stmt, ...], label: str | None, join: str) -> None:
        if not body:
            self._edge(origin, join, label)
            return
        exit_id, exit_label = self._block(origin, body, label)
        self._edge(exit_id, join, exit_label)

    def _statement(
        self, incoming: str, statement: Stmt, label: str | None
    ) -> tuple[str, str | None]:
        if isinstance(statement, DefineStmt):
            return self._leaf("process", _define(statement), statement.span, incoming, label)
        if isinstance(statement, DimensionStmt):
            return self._leaf("process", _dimension(statement), statement.span, incoming, label)
        if isinstance(statement, AssignStmt):
            text = f"{_lvalue(statement.target)} <- {_render(statement.value)}"
            return self._leaf("process", text, statement.span, incoming, label)
        if isinstance(statement, ReadStmt):
            names = ", ".join(_lvalue(target) for target in statement.targets)
            return self._leaf("io", f"Leer {names}", statement.span, incoming, label, "input")
        if isinstance(statement, WriteStmt):
            values = ", ".join(_render(value) for value in statement.values)
            stay = "" if statement.newline else " Sin Saltar"
            return self._leaf(
                "io", f"Escribir {values}{stay}", statement.span, incoming, label, "output"
            )
        if isinstance(statement, ClearStmt):
            return self._leaf("process", "Borrar Pantalla", statement.span, incoming, label)
        if isinstance(statement, WaitStmt):
            return self._leaf(
                "process",
                f"Esperar {_render(statement.seconds)} Segundos",
                statement.span,
                incoming,
                label,
            )
        if isinstance(statement, CallStmt):
            return self._leaf(
                "subprocess", _render(statement.call), statement.span, incoming, label
            )
        if isinstance(statement, IfStmt):
            return self._if(incoming, statement, label)
        if isinstance(statement, SwitchStmt):
            return self._switch(incoming, statement, label)
        if isinstance(statement, WhileStmt):
            return self._while(incoming, statement, label)
        if isinstance(statement, RepeatStmt):
            return self._repeat(incoming, statement, label)
        return self._for(incoming, statement, label)

    def _leaf(
        self,
        kind: FlowKind,
        text: str,
        span: SourceSpan,
        incoming: str,
        label: str | None,
        figure: str | None = None,
    ) -> tuple[str, str | None]:
        node = self._node(kind, text, span, figure)
        self._edge(incoming, node, label)
        return node, None

    def _if(self, incoming: str, statement: IfStmt, label: str | None) -> tuple[str, str | None]:
        diamond = self._node("decision", _render(statement.condition), statement.span)
        self._edge(incoming, diamond, label)
        join = self._node("join", "", statement.span)
        self._finish(diamond, statement.then_body, "Sí", join)
        if statement.else_body is None:
            self._edge(diamond, join, "No")
        else:
            self._finish(diamond, statement.else_body, "No", join)
        return join, None

    def _switch(
        self, incoming: str, statement: SwitchStmt, label: str | None
    ) -> tuple[str, str | None]:
        diamond = self._node("decision", _render(statement.selector), statement.span, "switch")
        self._edge(incoming, diamond, label)
        join = self._node("join", "", statement.span)
        for case in statement.cases:
            case_label = ", ".join(_render(item) for item in case.labels)
            self._finish(diamond, case.body, case_label, join)
        if statement.default_body is None:
            self._edge(diamond, join, None)
        else:
            self._finish(diamond, statement.default_body, "De Otro Modo", join)
        return join, None

    def _while(
        self, incoming: str, statement: WhileStmt, label: str | None
    ) -> tuple[str, str | None]:
        diamond = self._node("decision", _render(statement.condition), statement.span, "loop")
        self._edge(incoming, diamond, label)
        self._finish(diamond, statement.body, "Sí", diamond)
        return diamond, "No"

    def _repeat(
        self, incoming: str, statement: RepeatStmt, label: str | None
    ) -> tuple[str, str | None]:
        diamond_text = _render(statement.condition)
        if not statement.body:
            diamond = self._node("decision", diamond_text, statement.span, "loop")
            self._edge(incoming, diamond, label)
            self._edge(diamond, diamond, "No")
            return diamond, "Sí"
        marker = len(self.edges)
        exit_id, exit_label = self._block(incoming, statement.body, label)
        entry = self.edges[marker].target
        diamond = self._node("decision", diamond_text, statement.span, "loop")
        self._edge(exit_id, diamond, exit_label)
        self._edge(diamond, entry, "No")
        return diamond, "Sí"

    def _for(self, incoming: str, statement: ForStmt, label: str | None) -> tuple[str, str | None]:
        init = self._node(
            "process",
            f"{statement.variable} <- {_render(statement.start)}",
            statement.span,
        )
        self._edge(incoming, init, label)
        diamond = self._node("decision", _for_condition(statement), statement.span, "loop")
        self._edge(init, diamond, None)
        step = self._node("process", _for_step(statement), statement.span)
        if statement.body:
            exit_id, exit_label = self._block(diamond, statement.body, "Sí")
            self._edge(exit_id, step, exit_label)
        else:
            self._edge(diamond, step, "Sí")
        self._edge(step, diamond, None)
        return diamond, "No"


def _define(statement: DefineStmt) -> str:
    names = ", ".join(statement.names)
    return f"Definir {names} Como {_TYPES[statement.type_name]}"


def _dimension(statement: DimensionStmt) -> str:
    parts: list[str] = []
    for decl in statement.declarations:
        lengths = ", ".join(_render(length) for length in decl.lengths)
        piece = f"{decl.name}[{lengths}]"
        if decl.type_name is not None:
            piece += f" Como {_TYPES[decl.type_name]}"
        parts.append(piece)
    return "Dimension " + ", ".join(parts)


def _lvalue(target: LValue) -> str:
    if not target.indexes:
        return target.name
    indexes = ", ".join(_render(index) for index in target.indexes)
    return f"{target.name}[{indexes}]"


def _for_condition(statement: ForStmt) -> str:
    end = _render(statement.end)
    amount = _step_amount(statement.step)
    if amount is not None and amount > 0:
        return f"{statement.variable} <= {end}"
    if amount is not None and amount < 0:
        return f"{statement.variable} >= {end}"
    return f"{statement.variable} hasta {end}"


def _step_amount(step: Expr | None) -> int | None:
    if (
        isinstance(step, LiteralExpr)
        and isinstance(step.value, int)
        and not isinstance(step.value, bool)
    ):
        return step.value
    if isinstance(step, UnaryExpr) and step.operator in ("neg", "pos"):
        operand = step.operand
        if (
            isinstance(operand, LiteralExpr)
            and isinstance(operand.value, int)
            and not isinstance(operand.value, bool)
        ):
            return -operand.value if step.operator == "neg" else operand.value
    return None


def _for_step(statement: ForStmt) -> str:
    if statement.step is None:
        return f"{statement.variable} <- {statement.variable} ± 1"
    return f"{statement.variable} <- {statement.variable} + {_render(statement.step)}"


def _render(expr: Expr, minimum: int = 0) -> str:
    text, power = _piece(expr)
    if power < minimum:
        return f"({text})"
    return text


def _piece(expr: Expr) -> tuple[str, int]:
    if isinstance(expr, LiteralExpr):
        return expr.raw, _ATOM
    if isinstance(expr, NameExpr):
        return expr.name, _ATOM
    if isinstance(expr, IndexExpr):
        indexes = ", ".join(_render(index) for index in expr.indexes)
        return f"{expr.name}[{indexes}]", _ATOM
    if isinstance(expr, CallExpr):
        args = ", ".join(_render(arg) for arg in expr.args)
        return f"{expr.name}({args})", _ATOM
    if isinstance(expr, UnaryExpr):
        if expr.operator == "not":
            return f"NO {_render(expr.operand, 41)}", 40
        sign = "-" if expr.operator == "neg" else "+"
        return f"{sign}{_render(expr.operand, 81)}", 80
    symbol, power, assoc = _BINARY[expr.operator]
    if assoc == "left":
        left_min, right_min = power, power + 1
    elif assoc == "right":
        left_min, right_min = power + 1, power
    else:
        left_min = right_min = power + 1
    left = _render(expr.left, left_min)
    right = _render(expr.right, right_min)
    return f"{left} {symbol} {right}", power
