"""Biblioteca estándar. Solo transforma valores del intérprete."""

from __future__ import annotations

import math
import random
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

from language_core.ast_nodes import TypeName
from language_core.grammar import canonicalize
from language_core.runtime import Value
from language_core.type_system import format_value

_MAX_BITS = 20_000
_MAX_EXPONENT = 10_000


class StdFault(Exception):
    """Error de una función de biblioteca, con código de diagnóstico."""

    def __init__(self, code: str, message: str, suggestion: str | None) -> None:
        self.code = code
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)


def std_return_type(name: str, arg_types: list[TypeName | None]) -> TypeName | None:
    """Tipo de retorno conocido, o None si depende del texto."""
    canonical = canonicalize(name)
    if canonical == "abs":
        if arg_types and arg_types[0] in ("entero", "real"):
            return arg_types[0]
        return None
    if canonical in ("redon", "trunc", "longitud"):
        return "entero"
    if canonical == "aleatorio":
        return "entero" if len(arg_types) == 2 else "real"
    if canonical == "convertiranumero":
        return None
    if canonical in ("convertiratexto", "concatenar", "mayusculas", "minusculas", "subcadena"):
        return "cadena"
    if canonical == "potencia":
        if arg_types == ["entero", "entero"]:
            return "entero"
        return "real"
    return "real"


def std_arity(name: str) -> tuple[int, int] | None:
    """Mínimo y máximo de argumentos. None si el nombre no es de la biblioteca."""
    canonical = canonicalize(name)
    table = {
        "abs": (1, 1),
        "raiz": (1, 1),
        "potencia": (2, 2),
        "redon": (1, 1),
        "trunc": (1, 1),
        "sen": (1, 1),
        "cos": (1, 1),
        "tan": (1, 1),
        "ln": (1, 1),
        "exp": (1, 1),
        "aleatorio": (0, 2),
        "longitud": (1, 1),
        "subcadena": (3, 3),
        "concatenar": (2, 8),
        "mayusculas": (1, 1),
        "minusculas": (1, 1),
        "convertiranumero": (1, 1),
        "convertiratexto": (1, 1),
    }
    return table.get(canonical)


def call_stdlib(
    name: str,
    args: list[Value],
    *,
    rng: random.Random,
    index_base: int,
) -> Value:
    """Ejecuta una función de biblioteca ya validada en aridad."""
    canonical = canonicalize(name)
    if canonical == "abs":
        return _abs(args[0])
    if canonical == "raiz":
        return Value("real", _sqrt(_number(args[0], "Raíz")))
    if canonical == "potencia":
        return _power(args[0], args[1])
    if canonical == "redon":
        return Value("entero", _round_half_up(_number(args[0], "Redon")))
    if canonical == "trunc":
        return Value("entero", _truncate(_number(args[0], "Trunc")))
    if canonical == "sen":
        return Value("real", _trig(math.sin, args[0], "Sen"))
    if canonical == "cos":
        return Value("real", _trig(math.cos, args[0], "Cos"))
    if canonical == "tan":
        return Value("real", _trig(math.tan, args[0], "Tan"))
    if canonical == "ln":
        return Value("real", _ln(_number(args[0], "Ln")))
    if canonical == "exp":
        return Value("real", _exp(_number(args[0], "Exp")))
    if canonical == "aleatorio":
        return _random(args, rng)
    if canonical == "longitud":
        return Value("entero", len(_text(args[0], "Longitud")))
    if canonical == "subcadena":
        return Value("cadena", _substring(args, index_base))
    if canonical == "concatenar":
        return Value("cadena", "".join(format_value(item.type_name, item.value) for item in args))
    if canonical == "mayusculas":
        return Value("cadena", _text(args[0], "Mayusculas").upper())
    if canonical == "minusculas":
        return Value("cadena", _text(args[0], "Minusculas").lower())
    if canonical == "convertiranumero":
        return _to_number(_text(args[0], "ConvertirANumero"))
    if canonical == "convertiratexto":
        return Value("cadena", format_value(args[0].type_name, args[0].value))
    raise StdFault("E0310", f"No existe la función {name}.", "Revisa el nombre.")


def _abs(value: Value) -> Value:
    if value.type_name == "entero" and isinstance(value.value, int):
        return Value("entero", abs(value.value))
    if value.type_name == "real" and isinstance(value.value, Decimal):
        return Value("real", abs(value.value))
    raise StdFault("E0305", "Abs solo acepta números.", "Pasa un Entero o un Real.")


def _number(value: Value, name: str) -> Decimal:
    if value.type_name == "entero" and isinstance(value.value, int):
        return Decimal(value.value)
    if value.type_name == "real" and isinstance(value.value, Decimal):
        return value.value
    raise StdFault("E0305", f"{name} solo acepta números.", "Pasa un Entero o un Real.")


def _text(value: Value, name: str) -> str:
    if value.type_name in ("cadena", "caracter") and isinstance(value.value, str):
        return value.value
    raise StdFault("E0305", f"{name} espera un texto.", "Pasa una Cadena.")


def _sqrt(number: Decimal) -> Decimal:
    if number < 0:
        raise StdFault(
            "E0403",
            "No se puede calcular la raíz de un negativo.",
            "Usa un valor mayor o igual que cero.",
        )
    return number.sqrt()


def _ln(number: Decimal) -> Decimal:
    if number <= 0:
        raise StdFault(
            "E0403", "Ln solo está definido para números mayores que cero.", "Revisa el argumento."
        )
    try:
        return Decimal(str(math.log(float(number))))
    except (ValueError, OverflowError) as exc:
        raise StdFault("E0403", "Ln no se puede calcular.", "Revisa el argumento.") from exc


def _exp(number: Decimal) -> Decimal:
    try:
        return Decimal(str(math.exp(float(number))))
    except (ValueError, OverflowError) as exc:
        raise StdFault(
            "E0403", "Exp no se puede calcular.", "El exponente es demasiado grande."
        ) from exc


def _trig(function: object, value: Value, name: str) -> Decimal:
    number = float(_number(value, name))
    try:
        if not callable(function):
            raise StdFault("E0403", f"{name} no se puede calcular.", None)
        result = function(number)
    except ValueError as exc:
        raise StdFault(
            "E0403", f"{name} no se puede calcular.", "Revisa el ángulo en radianes."
        ) from exc
    if isinstance(result, float) and math.isfinite(result):
        return Decimal(str(result))
    raise StdFault("E0403", f"{name} no se puede calcular.", "Revisa el ángulo en radianes.")


def _round_half_up(number: Decimal) -> int:
    return int(number.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _truncate(number: Decimal) -> int:
    return int(number.to_integral_value(rounding=ROUND_DOWN))


def _power(base: Value, exponent: Value) -> Value:
    if base.type_name == "entero" and exponent.type_name == "entero":
        if not isinstance(base.value, int) or not isinstance(exponent.value, int):
            raise StdFault("E0403", "La potencia no es válida.", None)
        if base.value == 0 and exponent.value == 0:
            raise StdFault(
                "E0403", "0 elevado a 0 no está definido.", "Cambia la base o el exponente."
            )
        if exponent.value < 0:
            return Value("real", _decimal_power(Decimal(base.value), Decimal(exponent.value)))
        if exponent.value > _MAX_EXPONENT or (
            base.value not in (-1, 0, 1) and base.value.bit_length() * exponent.value > _MAX_BITS
        ):
            raise StdFault(
                "E0413",
                "La potencia produce un número demasiado grande.",
                "Usa un exponente más pequeño.",
            )
        return Value("entero", base.value**exponent.value)
    left = _number(base, "Potencia")
    right = _number(exponent, "Potencia")
    if left == 0 and right == 0:
        raise StdFault("E0403", "0 elevado a 0 no está definido.", "Cambia la base o el exponente.")
    if left < 0 and right != right.to_integral_value():
        raise StdFault(
            "E0403",
            "No se puede elevar un negativo a un real no entero.",
            "Usa un exponente entero o una base positiva.",
        )
    return Value("real", _decimal_power(left, right))


def _decimal_power(base: Decimal, exponent: Decimal) -> Decimal:
    try:
        return base**exponent
    except (InvalidOperation, OverflowError) as exc:
        raise StdFault(
            "E0403", "La potencia no se puede calcular.", "Revisa la base y el exponente."
        ) from exc


def _random(args: list[Value], rng: random.Random) -> Value:
    if not args:
        return Value("real", Decimal(str(rng.random())))
    if len(args) != 2:
        raise StdFault(
            "E0311",
            "Aleatorio se usa sin argumentos o con dos enteros.",
            "Escribe Aleatorio() o Aleatorio(1, 6).",
        )
    start = _int_arg(args[0], "Aleatorio")
    end = _int_arg(args[1], "Aleatorio")
    if start > end:
        raise StdFault(
            "E0403",
            "En Aleatorio el primero debe ser menor o igual que el segundo.",
            "Intercambia los dos enteros.",
        )
    return Value("entero", rng.randint(start, end))


def _int_arg(value: Value, name: str) -> int:
    if value.type_name == "entero" and isinstance(value.value, int):
        return value.value
    raise StdFault("E0305", f"{name} espera enteros en ese uso.", "Pasa dos números sin decimales.")


def _substring(args: list[Value], index_base: int) -> str:
    text = _text(args[0], "SubCadena")
    start = _int_arg(args[1], "SubCadena")
    end = _int_arg(args[2], "SubCadena")
    if not text:
        raise StdFault("E0404", "La cadena está vacía.", "Revisa el texto antes de recortarlo.")
    last = index_base + len(text) - 1
    if start < index_base or end > last or start > end:
        raise StdFault(
            "E0404",
            f"El recorte {start}..{end} está fuera del intervalo {index_base}..{last}.",
            "Los índices de SubCadena incluyen ambos extremos.",
        )
    offset = start - index_base
    count = end - start + 1
    return text[offset : offset + count]


def _to_number(text: str) -> Value:
    stripped = text.strip()
    if not stripped:
        raise StdFault(
            "E0407", "El texto no es un número.", "Escribe dígitos, por ejemplo 18 o 3.5."
        )
    try:
        if "." in stripped:
            return Value("real", Decimal(stripped))
        return Value("entero", int(stripped))
    except (InvalidOperation, ValueError) as exc:
        raise StdFault(
            "E0407",
            f"El texto {stripped!r} no es un número.",
            "Usa solo dígitos y un punto decimal.",
        ) from exc
