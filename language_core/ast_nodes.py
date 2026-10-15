"""Árbol de sintaxis abstracta del pseudolenguaje."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

TypeName = Literal["entero", "real", "logico", "caracter", "cadena"]
ParamMode = Literal["value", "reference"]


@dataclass(frozen=True)
class SourceSpan:
    """Posición inclusiva en el fuente. Líneas y columnas empiezan en 1."""

    start_line: int
    start_col: int
    end_line: int
    end_col: int


def merge_spans(left: SourceSpan, right: SourceSpan) -> SourceSpan:
    """Cubre desde el inicio del primer tramo hasta el final del segundo."""
    return SourceSpan(left.start_line, left.start_col, right.end_line, right.end_col)


@dataclass(frozen=True)
class Program:
    algorithm: Algorithm
    functions: tuple[FunctionDecl, ...]
    procedures: tuple[ProcedureDecl, ...]
    span: SourceSpan


@dataclass(frozen=True)
class Algorithm:
    name: str
    name_span: SourceSpan
    body: tuple[Stmt, ...]
    span: SourceSpan


@dataclass(frozen=True)
class Param:
    name: str
    mode: ParamMode
    span: SourceSpan
    explicit: bool = False


@dataclass(frozen=True)
class FunctionDecl:
    result_name: str
    name: str
    params: tuple[Param, ...]
    body: tuple[Stmt, ...]
    span: SourceSpan


@dataclass(frozen=True)
class ProcedureDecl:
    name: str
    params: tuple[Param, ...]
    body: tuple[Stmt, ...]
    span: SourceSpan


@dataclass(frozen=True)
class DefineStmt:
    names: tuple[str, ...]
    name_spans: tuple[SourceSpan, ...]
    type_name: TypeName
    span: SourceSpan


@dataclass(frozen=True)
class DimDecl:
    name: str
    lengths: tuple[Expr, ...]
    type_name: TypeName | None
    span: SourceSpan


@dataclass(frozen=True)
class DimensionStmt:
    declarations: tuple[DimDecl, ...]
    span: SourceSpan


@dataclass(frozen=True)
class LValue:
    name: str
    indexes: tuple[Expr, ...]
    span: SourceSpan


@dataclass(frozen=True)
class AssignStmt:
    target: LValue
    value: Expr
    span: SourceSpan


@dataclass(frozen=True)
class ReadStmt:
    targets: tuple[LValue, ...]
    span: SourceSpan


@dataclass(frozen=True)
class WriteStmt:
    values: tuple[Expr, ...]
    span: SourceSpan
    newline: bool = True


@dataclass(frozen=True)
class ClearStmt:
    span: SourceSpan


@dataclass(frozen=True)
class WaitStmt:
    seconds: Expr
    span: SourceSpan


@dataclass(frozen=True)
class CallExpr:
    name: str
    args: tuple[Expr, ...]
    span: SourceSpan


@dataclass(frozen=True)
class CallStmt:
    call: CallExpr
    span: SourceSpan


@dataclass(frozen=True)
class IfStmt:
    condition: Expr
    then_body: tuple[Stmt, ...]
    else_body: tuple[Stmt, ...] | None
    span: SourceSpan


@dataclass(frozen=True)
class SwitchCase:
    labels: tuple[Expr, ...]
    body: tuple[Stmt, ...]
    span: SourceSpan


@dataclass(frozen=True)
class SwitchStmt:
    selector: Expr
    cases: tuple[SwitchCase, ...]
    default_body: tuple[Stmt, ...] | None
    span: SourceSpan


@dataclass(frozen=True)
class WhileStmt:
    condition: Expr
    body: tuple[Stmt, ...]
    span: SourceSpan


@dataclass(frozen=True)
class RepeatStmt:
    body: tuple[Stmt, ...]
    condition: Expr
    span: SourceSpan


@dataclass(frozen=True)
class ForStmt:
    variable: str
    variable_span: SourceSpan
    start: Expr
    end: Expr
    step: Expr | None
    body: tuple[Stmt, ...]
    span: SourceSpan


@dataclass(frozen=True)
class LiteralExpr:
    kind: TypeName
    value: int | Decimal | bool | str
    raw: str
    span: SourceSpan


@dataclass(frozen=True)
class NameExpr:
    name: str
    span: SourceSpan


@dataclass(frozen=True)
class UnaryExpr:
    operator: Literal["neg", "pos", "not"]
    operand: Expr
    span: SourceSpan


@dataclass(frozen=True)
class BinaryExpr:
    operator: Literal[
        "add",
        "sub",
        "mul",
        "div",
        "idiv",
        "mod",
        "pow",
        "eq",
        "neq",
        "lt",
        "lte",
        "gt",
        "gte",
        "and",
        "or",
    ]
    left: Expr
    right: Expr
    span: SourceSpan


@dataclass(frozen=True)
class IndexExpr:
    name: str
    indexes: tuple[Expr, ...]
    span: SourceSpan


Stmt = (
    DefineStmt
    | DimensionStmt
    | AssignStmt
    | ReadStmt
    | WriteStmt
    | ClearStmt
    | WaitStmt
    | CallStmt
    | IfStmt
    | SwitchStmt
    | WhileStmt
    | RepeatStmt
    | ForStmt
)

Expr = LiteralExpr | NameExpr | UnaryExpr | BinaryExpr | CallExpr | IndexExpr

Node = (
    Program | Algorithm | FunctionDecl | ProcedureDecl | Stmt | Expr | LValue | SwitchCase | DimDecl
)


def dump(node: Node) -> str:
    """Volcado estable, una línea por nodo, para las pruebas del parser."""
    return "\n".join(_lines(node))


def _child(text: str) -> list[str]:
    return [f"  {line}" for line in text.split("\n")] if text else []


def _lines(node: Node) -> list[str]:
    if isinstance(node, Program):
        rows = [f"Program {node.algorithm.name}"]
        rows.extend(_child(dump(node.algorithm)))
        for fn in node.functions:
            rows.extend(_child(dump(fn)))
        for proc in node.procedures:
            rows.extend(_child(dump(proc)))
        return rows
    if isinstance(node, Algorithm):
        rows = [f"Algorithm {node.name}"]
        for stmt in node.body:
            rows.extend(_child(dump(stmt)))
        return rows
    if isinstance(node, FunctionDecl):
        params = ", ".join(f"{p.name}:{p.mode}" for p in node.params)
        rows = [f"Function {node.result_name} <- {node.name}({params})"]
        for stmt in node.body:
            rows.extend(_child(dump(stmt)))
        return rows
    if isinstance(node, ProcedureDecl):
        params = ", ".join(f"{p.name}:{p.mode}" for p in node.params)
        rows = [f"Procedure {node.name}({params})"]
        for stmt in node.body:
            rows.extend(_child(dump(stmt)))
        return rows
    if isinstance(node, DefineStmt):
        names = ", ".join(node.names)
        return [f"Define {node.type_name} {names}"]
    if isinstance(node, DimensionStmt):
        rows = ["Dimension"]
        for decl in node.declarations:
            rows.extend(_child(dump(decl)))
        return rows
    if isinstance(node, DimDecl):
        kind = node.type_name or "?"
        rows = [f"Dim {node.name} {kind}"]
        for length in node.lengths:
            rows.extend(_child(dump(length)))
        return rows
    if isinstance(node, AssignStmt):
        rows = ["Assign"]
        rows.extend(_child(dump(node.target)))
        rows.extend(_child(dump(node.value)))
        return rows
    if isinstance(node, LValue):
        rows = [f"LValue {node.name}"]
        for index in node.indexes:
            rows.extend(_child(dump(index)))
        return rows
    if isinstance(node, ReadStmt):
        rows = ["Read"]
        for target in node.targets:
            rows.extend(_child(dump(target)))
        return rows
    if isinstance(node, WriteStmt):
        rows = ["Write"] if node.newline else ["Write SinSaltar"]
        for value in node.values:
            rows.extend(_child(dump(value)))
        return rows
    if isinstance(node, ClearStmt):
        return ["Clear"]
    if isinstance(node, WaitStmt):
        return ["Wait", *_child(dump(node.seconds))]
    if isinstance(node, CallStmt):
        return ["CallStmt", *_child(dump(node.call))]
    if isinstance(node, IfStmt):
        rows = ["If", *_child(dump(node.condition)), "then"]
        for stmt in node.then_body:
            rows.extend(_child(dump(stmt)))
        if node.else_body is not None:
            rows.append("else")
            for stmt in node.else_body:
                rows.extend(_child(dump(stmt)))
        return rows
    if isinstance(node, SwitchStmt):
        rows = ["Switch", *_child(dump(node.selector))]
        for case in node.cases:
            rows.extend(_child(dump(case)))
        if node.default_body is not None:
            rows.append("default")
            for stmt in node.default_body:
                rows.extend(_child(dump(stmt)))
        return rows
    if isinstance(node, SwitchCase):
        rows = ["Case"]
        for label in node.labels:
            rows.extend(_child(dump(label)))
        for stmt in node.body:
            rows.extend(_child(dump(stmt)))
        return rows
    if isinstance(node, WhileStmt):
        rows = ["While", *_child(dump(node.condition))]
        for stmt in node.body:
            rows.extend(_child(dump(stmt)))
        return rows
    if isinstance(node, RepeatStmt):
        rows = ["Repeat"]
        for stmt in node.body:
            rows.extend(_child(dump(stmt)))
        rows.append("until")
        rows.extend(_child(dump(node.condition)))
        return rows
    if isinstance(node, ForStmt):
        rows = [f"For {node.variable}", *_child(dump(node.start)), *_child(dump(node.end))]
        if node.step is not None:
            rows.append("step")
            rows.extend(_child(dump(node.step)))
        for stmt in node.body:
            rows.extend(_child(dump(stmt)))
        return rows
    if isinstance(node, LiteralExpr):
        return [f"Literal {node.kind} {node.raw}"]
    if isinstance(node, NameExpr):
        return [f"Name {node.name}"]
    if isinstance(node, UnaryExpr):
        return [f"Unary {node.operator}", *_child(dump(node.operand))]
    if isinstance(node, BinaryExpr):
        return [f"Binary {node.operator}", *_child(dump(node.left)), *_child(dump(node.right))]
    if isinstance(node, CallExpr):
        rows = [f"Call {node.name}"]
        for arg in node.args:
            rows.extend(_child(dump(arg)))
        return rows
    if isinstance(node, IndexExpr):
        rows = [f"Index {node.name}"]
        for index in node.indexes:
            rows.extend(_child(dump(index)))
        return rows
    raise TypeError(f"Nodo sin volcado: {type(node)!r}")
