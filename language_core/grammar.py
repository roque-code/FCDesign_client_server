"""Tablas normativas del lenguaje: palabras, operadores y perfiles."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass

# Texto plegado, sin acentos. El lexer compara contra esta tabla.
KEYWORDS: frozenset[str] = frozenset(
    {
        "algoritmo",
        "finalgoritmo",
        "funcion",
        "finfuncion",
        "subproceso",
        "finsubproceso",
        "definir",
        "como",
        "dimension",
        "por",
        "valor",
        "referencia",
        "leer",
        "escribir",
        "sin",
        "saltar",
        "borrar",
        "pantalla",
        "esperar",
        "segundos",
        "si",
        "entonces",
        "sino",
        "finsi",
        "segun",
        "hacer",
        "de",
        "otro",
        "modo",
        "finsegun",
        "mientras",
        "finmientras",
        "repetir",
        "hasta",
        "que",
        "para",
        "con",
        "paso",
        "finpara",
        "entero",
        "real",
        "logico",
        "caracter",
        "cadena",
        "verdadero",
        "falso",
        "y",
        "o",
        "no",
        "div",
        "mod",
    }
)

STDLIB_NAMES: frozenset[str] = frozenset(
    {
        "abs",
        "raiz",
        "potencia",
        "redon",
        "trunc",
        "sen",
        "cos",
        "tan",
        "ln",
        "exp",
        "aleatorio",
        "longitud",
        "subcadena",
        "concatenar",
        "mayusculas",
        "minusculas",
        "convertiranumero",
        "convertiratexto",
    }
)

# Grafía que ve el estudiante. El lexer acepta cualquier acento o mayúscula.
KEYWORD_DISPLAY: tuple[str, ...] = (
    "Algoritmo",
    "FinAlgoritmo",
    "Función",
    "FinFunción",
    "SubProceso",
    "FinSubProceso",
    "Definir",
    "Como",
    "Dimension",
    "Por",
    "Valor",
    "Referencia",
    "Leer",
    "Escribir",
    "Sin",
    "Saltar",
    "Borrar",
    "Pantalla",
    "Esperar",
    "Segundos",
    "Si",
    "Entonces",
    "Sino",
    "FinSi",
    "Según",
    "Hacer",
    "De",
    "Otro",
    "Modo",
    "FinSegun",
    "Mientras",
    "FinMientras",
    "Repetir",
    "Hasta",
    "Que",
    "Para",
    "Con",
    "Paso",
    "FinPara",
    "Entero",
    "Real",
    "Lógico",
    "Caracter",
    "Cadena",
    "Verdadero",
    "Falso",
    "Y",
    "O",
    "NO",
    "DIV",
    "MOD",
)

STDLIB_DISPLAY: tuple[str, ...] = (
    "Abs",
    "Raíz",
    "Potencia",
    "Redon",
    "Trunc",
    "Sen",
    "Cos",
    "Tan",
    "Ln",
    "Exp",
    "Aleatorio",
    "Longitud",
    "Subcadena",
    "Concatenar",
    "Mayúsculas",
    "Minúsculas",
    "ConvertirANumero",
    "ConvertirATexto",
)

TYPE_KEYWORDS: dict[str, str] = {
    "entero": "entero",
    "real": "real",
    "logico": "logico",
    "caracter": "caracter",
    "cadena": "cadena",
}

# Ligadura de mayor a menor. El parser Pratt usa estos números.
BP_OR = 20
BP_AND = 30
BP_NOT = 40
BP_REL = 50
BP_ADD = 60
BP_MUL = 70
BP_UNARY = 80
BP_POW = 90

PRECEDENCE: tuple[tuple[str, int, str], ...] = (
    ("^", BP_POW, "derecha"),
    ("unario + -", BP_UNARY, "prefijo"),
    ("* / DIV MOD %", BP_MUL, "izquierda"),
    ("+ -", BP_ADD, "izquierda"),
    ("relaciones", BP_REL, "no encadenan"),
    ("NO", BP_NOT, "prefijo"),
    ("Y", BP_AND, "izquierda"),
    ("O", BP_OR, "izquierda"),
)


def canonicalize(text: str) -> str:
    """Pliega mayúsculas y elimina acentos para reconocer palabras clave."""
    folded = text.casefold()
    decomposed = unicodedata.normalize("NFD", folded)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


@dataclass(frozen=True)
class LanguageProfile:
    """Banderas educativas. El perfil estricto es el predeterminado."""

    name: str
    index_base: int = 1
    require_semicolons: bool = True
    require_declarations: bool = True
    implicit_widening: bool = True
    # Se conserva para perfiles ya guardados. = asigna y == compara en todos los perfiles.
    allow_equals_assignment: bool = False
    allow_globals: bool = False
    beginner_warnings: bool = True
    max_instructions: int = 100_000
    max_call_depth: int = 100
    max_array_cells: int = 10_000
    max_time_ms: int = 5_000
    max_string_length: int = 100_000
    max_output_chars: int = 256_000


STRICT = LanguageProfile(name="strict")

FLEXIBLE = LanguageProfile(
    name="flexible",
    require_semicolons=False,
    require_declarations=False,
    allow_equals_assignment=True,
    beginner_warnings=False,
)


def _flag_bool(config: Mapping[str, object], key: str, default: bool) -> bool:
    value = config.get(key, default)
    return value if isinstance(value, bool) else default


def _flag_int(config: Mapping[str, object], key: str, default: int) -> int:
    value = config.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return value


def profile_from_mapping(name: str, config: Mapping[str, object]) -> LanguageProfile:
    """Reconstruye un perfil desde el diccionario que viaja al runner."""
    base = _flag_int(config, "index_base", 1)
    if base not in (0, 1):
        base = 1
    return LanguageProfile(
        name=name,
        index_base=base,
        require_semicolons=_flag_bool(config, "require_semicolons", True),
        require_declarations=_flag_bool(config, "require_declarations", True),
        implicit_widening=_flag_bool(config, "implicit_widening", True),
        allow_equals_assignment=_flag_bool(config, "allow_equals_assignment", False),
        allow_globals=_flag_bool(config, "allow_globals", False),
        beginner_warnings=_flag_bool(config, "beginner_warnings", True),
        max_instructions=_flag_int(config, "max_instructions", 100_000),
        max_call_depth=_flag_int(config, "max_call_depth", 100),
        max_array_cells=_flag_int(config, "max_array_cells", 10_000),
        max_time_ms=_flag_int(config, "max_time_ms", 5_000),
        max_string_length=_flag_int(config, "max_string_length", 100_000),
        max_output_chars=_flag_int(config, "max_output_chars", 256_000),
    )
