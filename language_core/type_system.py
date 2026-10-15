"""Reglas de tipos, formato canónico y lectura de datos."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from language_core.ast_nodes import Expr, LiteralExpr, TypeName, UnaryExpr
from language_core.grammar import canonicalize

_INTEGER_TEXT = re.compile(r"[+-]?\d+")
_REAL_TEXT = re.compile(r"[+-]?\d+(\.\d+)?")


@dataclass(frozen=True)
class TypeIssue:
    """Un problema de tipos, todavía sin posición."""

    severity: str
    code: str
    message: str
    suggestion: str | None = None


def const_int(expr: Expr) -> int | None:
    """Valor entero conocido en compilación, o None si no es constante."""
    if isinstance(expr, LiteralExpr) and expr.kind == "entero" and isinstance(expr.value, int):
        return expr.value
    if isinstance(expr, UnaryExpr) and expr.operator == "neg":
        inner = const_int(expr.operand)
        if inner is not None:
            return -inner
    if isinstance(expr, UnaryExpr) and expr.operator == "pos":
        return const_int(expr.operand)
    return None


def is_numeric(type_name: TypeName) -> bool:
    return type_name in ("entero", "real")


def check_unary(operator: str, operand: TypeName) -> tuple[TypeName | None, tuple[TypeIssue, ...]]:
    """Tipo de un operador prefijo."""
    if operator == "not":
        if operand == "logico":
            return "logico", ()
        return None, (
            TypeIssue(
                "error",
                "E0305",
                "NO solo puede negar un valor lógico.",
                "Compara primero, o usa Verdadero y Falso.",
            ),
        )
    if operand == "entero":
        return "entero", ()
    if operand == "real":
        return "real", ()
    return None, (
        TypeIssue(
            "error",
            "E0305",
            "El signo solo se aplica a números.",
            "Este operador espera un Entero o un Real.",
        ),
    )


def check_binary(
    operator: str,
    left: TypeName,
    right: TypeName,
    right_expr: Expr,
    *,
    beginner_warnings: bool,
) -> tuple[TypeName | None, tuple[TypeIssue, ...]]:
    """Tipo de un operador binario y las advertencias asociadas."""
    if operator in ("and", "or"):
        if left == "logico" and right == "logico":
            return "logico", ()
        name = "Y" if operator == "and" else "O"
        return None, (
            TypeIssue(
                "error",
                "E0305",
                f"{name} solo une valores lógicos.",
                "Cada lado debe ser una condición, por ejemplo edad >= 18.",
            ),
        )
    if operator in ("add", "sub", "mul"):
        widened = _widen(left, right)
        if widened is not None:
            return widened, ()
        return None, (_arithmetic_issue(operator),)
    if operator == "div":
        if is_numeric(left) and is_numeric(right):
            return "real", ()
        return None, (_arithmetic_issue(operator),)
    if operator in ("idiv", "mod"):
        if left == "entero" and right == "entero":
            return "entero", ()
        symbol = "DIV" if operator == "idiv" else "MOD"
        return None, (
            TypeIssue(
                "error",
                "E0305",
                f"{symbol} solo acepta números enteros.",
                "Si necesitas decimales, usa /.",
            ),
        )
    if operator == "pow":
        return _power_type(left, right, right_expr)
    if operator in ("eq", "neq", "lt", "lte", "gt", "gte"):
        return _comparison_type(operator, left, right, beginner_warnings)
    return None, (TypeIssue("error", "E0305", "Esta operación no está permitida.", None),)


def check_assignment(
    target: TypeName,
    source: TypeName,
    source_expr: Expr,
    *,
    implicit_widening: bool,
) -> tuple[TypeIssue, ...]:
    """Errores de una asignación. Vacío si es compatible."""
    if target == source:
        if target == "caracter" and isinstance(source_expr, LiteralExpr):
            if isinstance(source_expr.value, str) and len(source_expr.value) != 1:
                return (
                    TypeIssue(
                        "error",
                        "E0303",
                        "Un Carácter admite exactamente un símbolo.",
                        "Usa Cadena si el texto es más largo.",
                    ),
                )
        return ()
    if target == "real" and source == "entero" and implicit_widening:
        return ()
    if target == "caracter" and source == "cadena":
        if isinstance(source_expr, LiteralExpr) and isinstance(source_expr.value, str):
            if len(source_expr.value) != 1:
                return (
                    TypeIssue(
                        "error",
                        "E0303",
                        "No se puede asignar esta cadena a un Carácter.",
                        "La cadena debe tener un solo símbolo, o cambia la variable a Cadena.",
                    ),
                )
        return ()
    if target == "cadena" and source == "caracter":
        return ()
    if target == "entero" and source == "real":
        return (
            TypeIssue(
                "error",
                "E0303",
                "No se puede asignar un Real a un Entero.",
                "Usa Trunc o Redon cuando estén disponibles, o declara la variable como Real.",
            ),
        )
    return (
        TypeIssue(
            "error",
            "E0303",
            f"No se puede asignar { _label(source) } a { _label(target) }.",
            "Revisa el tipo declarado con Definir.",
        ),
    )


def check_condition(type_name: TypeName) -> TypeIssue | None:
    """La condición de Si, Mientras, Repetir y Para debe ser lógica."""
    if type_name == "logico":
        return None
    return TypeIssue(
        "error",
        "E0304",
        "La condición debe ser un valor lógico.",
        "Compara con =, < o >, o usa Verdadero y Falso.",
    )


def format_value(type_name: TypeName, value: object) -> str:
    """Texto canónico que escribe Escribir y muestra el depurador."""
    if type_name == "logico":
        return "Verdadero" if value else "Falso"
    if type_name == "real":
        number = value if isinstance(value, Decimal) else Decimal(str(value))
        text = format(number, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        if text in {"", "-", "-0"}:
            return "0"
        return text
    return str(value)


def parse_input(type_name: TypeName, text: str) -> object | None:
    """Convierte una línea de Leer. None si no es compatible con el tipo."""
    if type_name == "cadena":
        return text
    if type_name == "caracter":
        if len(text) == 1:
            return text
        return None
    stripped = text.strip()
    if type_name == "entero" and _INTEGER_TEXT.fullmatch(stripped):
        return int(stripped)
    if type_name == "real" and _REAL_TEXT.fullmatch(stripped):
        return Decimal(stripped)
    if type_name == "logico":
        folded = canonicalize(stripped)
        if folded == "verdadero":
            return True
        if folded == "falso":
            return False
    return None


def _power_type(
    left: TypeName, right: TypeName, right_expr: Expr
) -> tuple[TypeName | None, tuple[TypeIssue, ...]]:
    if not (is_numeric(left) and is_numeric(right)):
        return None, (_arithmetic_issue("pow"),)
    if left == "entero" and right == "entero":
        exponent = const_int(right_expr)
        if exponent is not None and exponent < 0:
            return "real", ()
        return "entero", ()
    return "real", ()


def _comparison_type(
    operator: str, left: TypeName, right: TypeName, beginner_warnings: bool
) -> tuple[TypeName | None, tuple[TypeIssue, ...]]:
    issues: list[TypeIssue] = []
    if is_numeric(left) and is_numeric(right):
        if beginner_warnings and operator == "eq" and (left == "real" or right == "real"):
            issues.append(
                TypeIssue(
                    "warning",
                    "W0501",
                    "Comparar reales con = puede fallar por el redondeo.",
                    "Si buscas un resultado aproximado, compara una diferencia pequeña.",
                )
            )
        return "logico", tuple(issues)
    if left == right and left in ("cadena", "caracter"):
        return "logico", ()
    if left == "logico" and right == "logico" and operator in ("eq", "neq"):
        return "logico", ()
    return None, (
        TypeIssue(
            "error",
            "E0306",
            "Estos valores no se pueden comparar entre sí.",
            "Compara números con números, cadenas con cadenas o lógicos con = y <>.",
        ),
    )


def _widen(left: TypeName, right: TypeName) -> TypeName | None:
    if left == "entero" and right == "entero":
        return "entero"
    if is_numeric(left) and is_numeric(right):
        return "real"
    return None


def _arithmetic_issue(operator: str) -> TypeIssue:
    if operator == "add":
        return TypeIssue(
            "error",
            "E0305",
            "El operador + es numérico en el perfil estricto.",
            "Para unir texto usa Concatenar, o convierte los números con ConvertirATexto.",
        )
    return TypeIssue(
        "error",
        "E0305",
        "Esta operación solo acepta números.",
        "Revisa que los dos lados sean Entero o Real.",
    )


def _label(type_name: TypeName) -> str:
    names = {
        "entero": "un Entero",
        "real": "un Real",
        "logico": "un Lógico",
        "caracter": "un Carácter",
        "cadena": "una Cadena",
    }
    return names[type_name]
