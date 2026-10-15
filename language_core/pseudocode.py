"""AST del perfil estricto a texto.

La impresora no ejecuta. Los paréntesis solo aparecen cuando hacen falta
para que el parser reconstruya el mismo árbol.
"""

from __future__ import annotations

from decimal import Decimal

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
    Stmt,
    SwitchStmt,
    UnaryExpr,
    WaitStmt,
    WhileStmt,
    WriteStmt,
)
from language_core.grammar import (
    BP_ADD,
    BP_AND,
    BP_MUL,
    BP_NOT,
    BP_OR,
    BP_POW,
    BP_REL,
    BP_UNARY,
)

PRIMARY = 100

TYPE_LABEL: dict[str, str] = {
    "entero": "Entero",
    "real": "Real",
    "logico": "Lógico",
    "caracter": "Caracter",
    "cadena": "Cadena",
}

BINARY_SYMBOL: dict[str, str] = {
    "add": "+",
    "sub": "-",
    "mul": "*",
    "div": "/",
    "idiv": "DIV",
    "mod": "MOD",
    "pow": "^",
    "eq": "=",
    "neq": "<>",
    "lt": "<",
    "lte": "<=",
    "gt": ">",
    "gte": ">=",
    "and": "Y",
    "or": "O",
}

_POWER: dict[str, tuple[int, str]] = {
    "or": (BP_OR, "left"),
    "and": (BP_AND, "left"),
    "eq": (BP_REL, "none"),
    "neq": (BP_REL, "none"),
    "lt": (BP_REL, "none"),
    "lte": (BP_REL, "none"),
    "gt": (BP_REL, "none"),
    "gte": (BP_REL, "none"),
    "add": (BP_ADD, "left"),
    "sub": (BP_ADD, "left"),
    "mul": (BP_MUL, "left"),
    "div": (BP_MUL, "left"),
    "idiv": (BP_MUL, "left"),
    "mod": (BP_MUL, "left"),
    "pow": (BP_POW, "right"),
}


def quote_text(value: str, quote: str) -> str:
    """Lexema entre comillas, con los escapes que acepta el lexer."""
    parts = [quote]
    for ch in value:
        if ch == "\\":
            parts.append("\\\\")
        elif ch == quote:
            parts.append("\\" + quote)
        elif ch == "\n":
            parts.append("\\n")
        elif ch == "\t":
            parts.append("\\t")
        elif ord(ch) < 32:
            raise ValueError(ch)
        else:
            parts.append(ch)
    parts.append(quote)
    return "".join(parts)


def format_real(number: Decimal) -> str:
    """Texto de un real positivo, siempre con punto decimal."""
    text = format(abs(number), "f")
    if "." not in text:
        return f"{text}.0"
    whole, frac = text.split(".", 1)
    return f"{whole}.{frac.rstrip('0') or '0'}"


def needs_paren(child_bp: int, child_assoc: str, parent_bp: int, side: str) -> bool:
    """Decide si un hijo se imprime entre paréntesis."""
    if parent_bp <= 0 or child_bp > parent_bp:
        return False
    if child_bp < parent_bp:
        return True
    if child_assoc == "left":
        return side == "right"
    if child_assoc == "right":
        return side == "left"
    return child_assoc == "none"


def binary_power(operator: str) -> tuple[int, str]:
    """Precedencia y asociatividad de un operador binario."""
    return _POWER[operator]


def expr_power(expr: Expr) -> tuple[int, str]:
    """Precedencia y asociatividad de una expresión."""
    if isinstance(expr, UnaryExpr):
        if expr.operator == "not":
            return BP_NOT, "prefix"
        return BP_UNARY, "prefix"
    if isinstance(expr, BinaryExpr):
        return binary_power(expr.operator)
    return PRIMARY, "primary"


def render(program: Program) -> str:
    """Imprime el algoritmo con sangría de cuatro espacios y punto y coma."""
    lines: list[str] = []
    for function in program.functions:
        lines.extend(_function_lines(function))
    for procedure in program.procedures:
        lines.extend(_procedure_lines(procedure))
    lines.append(f"Algoritmo {program.algorithm.name}")
    for statement in program.algorithm.body:
        lines.extend(_statement_lines(statement, 1))
    lines.append("FinAlgoritmo")
    return "\n".join(lines) + "\n"


def _function_lines(function: FunctionDecl) -> list[str]:
    rows = [f"Funcion {function.result_name} <- {function.name}({_params(function.params)})"]
    for statement in function.body:
        rows.extend(_statement_lines(statement, 1))
    rows.append("FinFuncion")
    return rows


def _procedure_lines(procedure: ProcedureDecl) -> list[str]:
    rows = [f"SubProceso {procedure.name}({_params(procedure.params)})"]
    for statement in procedure.body:
        rows.extend(_statement_lines(statement, 1))
    rows.append("FinSubProceso")
    return rows


def _params(params: tuple) -> str:
    parts: list[str] = []
    for param in params:
        if param.mode == "reference":
            parts.append(f"{param.name} Por Referencia")
        elif param.explicit:
            parts.append(f"{param.name} Por Valor")
        else:
            parts.append(param.name)
    return ", ".join(parts)


def _statement_lines(statement: Stmt, level: int) -> list[str]:
    pad = "    " * level
    if isinstance(statement, IfStmt):
        rows = [f"{pad}Si {format_expr(statement.condition)} Entonces"]
        for item in statement.then_body:
            rows.extend(_statement_lines(item, level + 1))
        if statement.else_body is not None:
            rows.append(f"{pad}Sino")
            for item in statement.else_body:
                rows.extend(_statement_lines(item, level + 1))
        rows.append(f"{pad}FinSi")
        return rows
    if isinstance(statement, WhileStmt):
        rows = [f"{pad}Mientras {format_expr(statement.condition)} Hacer"]
        for item in statement.body:
            rows.extend(_statement_lines(item, level + 1))
        rows.append(f"{pad}FinMientras")
        return rows
    if isinstance(statement, SwitchStmt):
        rows = [f"{pad}Segun {format_expr(statement.selector)} Hacer"]
        inner = "    " * (level + 1)
        for case in statement.cases:
            labels = ", ".join(format_expr(label) for label in case.labels)
            rows.append(f"{inner}{labels}:")
            for item in case.body:
                rows.extend(_statement_lines(item, level + 2))
        if statement.default_body is not None:
            rows.append(f"{inner}De Otro Modo:")
            for item in statement.default_body:
                rows.extend(_statement_lines(item, level + 2))
        rows.append(f"{pad}FinSegun")
        return rows
    if isinstance(statement, RepeatStmt):
        rows = [f"{pad}Repetir"]
        for item in statement.body:
            rows.extend(_statement_lines(item, level + 1))
        rows.append(f"{pad}Hasta Que {format_expr(statement.condition)}")
        return rows
    if isinstance(statement, ForStmt):
        step = ""
        if statement.step is not None:
            step = f" Con Paso {format_expr(statement.step)}"
        rows = [
            f"{pad}Para {statement.variable} <- {format_expr(statement.start)} "
            f"Hasta {format_expr(statement.end)}{step} Hacer"
        ]
        for item in statement.body:
            rows.extend(_statement_lines(item, level + 1))
        rows.append(f"{pad}FinPara")
        return rows
    return [f"{pad}{_statement(statement)}"]


def _statement(statement: Stmt) -> str:
    if isinstance(statement, DefineStmt):
        names = ", ".join(statement.names)
        return f"Definir {names} Como {TYPE_LABEL[statement.type_name]};"
    if isinstance(statement, DimensionStmt):
        parts: list[str] = []
        for decl in statement.declarations:
            lengths = ", ".join(format_expr(length) for length in decl.lengths)
            typed = f" Como {TYPE_LABEL[decl.type_name]}" if decl.type_name else ""
            parts.append(f"{decl.name}[{lengths}]{typed}")
        return f"Dimension {', '.join(parts)};"
    if isinstance(statement, AssignStmt):
        return f"{_lvalue(statement.target)} <- {format_expr(statement.value)};"
    if isinstance(statement, ReadStmt):
        names = ", ".join(_lvalue(target) for target in statement.targets)
        return f"Leer {names};"
    if isinstance(statement, CallStmt):
        return f"{format_expr(statement.call)};"
    if isinstance(statement, WriteStmt):
        values = ", ".join(format_expr(value) for value in statement.values)
        stay = "" if statement.newline else " Sin Saltar"
        return f"Escribir {values}{stay};"
    if isinstance(statement, ClearStmt):
        return "Borrar Pantalla;"
    if isinstance(statement, WaitStmt):
        return f"Esperar {format_expr(statement.seconds)} Segundos;"
    raise ValueError(f"Sentencia fuera de esta fase: {type(statement).__name__}")


def format_expr(expr: Expr, parent_bp: int = 0, side: str = "left") -> str:
    """Imprime una expresión, con paréntesis si la precedencia lo pide."""
    power, assoc = expr_power(expr)
    body = _expr_body(expr)
    if needs_paren(power, assoc, parent_bp, side):
        return f"({body})"
    return body


def _expr_body(expr: Expr) -> str:
    if isinstance(expr, LiteralExpr):
        return expr.raw
    if isinstance(expr, NameExpr):
        return expr.name
    if isinstance(expr, UnaryExpr):
        minimum = BP_NOT if expr.operator == "not" else BP_UNARY
        operand = format_expr(expr.operand, minimum, "right")
        if expr.operator == "not":
            return f"NO {operand}"
        symbol = "-" if expr.operator == "neg" else "+"
        return f"{symbol}{operand}"
    if isinstance(expr, BinaryExpr):
        power, _assoc = expr_power(expr)
        left = format_expr(expr.left, power, "left")
        right = format_expr(expr.right, power, "right")
        return f"{left} {BINARY_SYMBOL[expr.operator]} {right}"
    if isinstance(expr, CallExpr):
        args = ", ".join(format_expr(arg) for arg in expr.args)
        return f"{expr.name}({args})"
    if isinstance(expr, IndexExpr):
        indexes = ", ".join(format_expr(item) for item in expr.indexes)
        return f"{expr.name}[{indexes}]"
    raise ValueError(f"Expresión fuera de esta fase: {type(expr).__name__}")


def _lvalue(target: LValue) -> str:
    if not target.indexes:
        return target.name
    indexes = ", ".join(format_expr(item) for item in target.indexes)
    return f"{target.name}[{indexes}]"
