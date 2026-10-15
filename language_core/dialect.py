"""Grafías en inglés de las mismas palabras reservadas.

El canónico interno sigue siendo el español. Un texto ya guardado no se
recorre ni se reescribe: el lexer reconoce las dos grafías.
"""

from __future__ import annotations

from language_core.grammar import KEYWORDS, canonicalize

# canónico, grafía del curso, grafía en inglés
_ROWS: tuple[tuple[str, str, str], ...] = (
    ("algoritmo", "Algoritmo", "Algorithm"),
    ("finalgoritmo", "FinAlgoritmo", "EndAlgorithm"),
    ("funcion", "Función", "Function"),
    ("finfuncion", "FinFunción", "EndFunction"),
    ("subproceso", "SubProceso", "SubProcedure"),
    ("finsubproceso", "FinSubProceso", "EndSubProcedure"),
    ("definir", "Definir", "Declare"),
    ("como", "Como", "As"),
    ("dimension", "Dimension", "Dimension"),
    ("por", "Por", "By"),
    ("valor", "Valor", "Value"),
    ("referencia", "Referencia", "Reference"),
    ("leer", "Leer", "Read"),
    ("escribir", "Escribir", "Write"),
    ("sin", "Sin", "Without"),
    ("saltar", "Saltar", "Newline"),
    ("borrar", "Borrar", "Clear"),
    ("pantalla", "Pantalla", "Screen"),
    ("esperar", "Esperar", "Wait"),
    ("segundos", "Segundos", "Seconds"),
    ("si", "Si", "If"),
    ("entonces", "Entonces", "Then"),
    ("sino", "Sino", "Else"),
    ("finsi", "FinSi", "EndIf"),
    ("segun", "Según", "Switch"),
    ("hacer", "Hacer", "Do"),
    ("de", "De", "In"),
    ("otro", "Otro", "Other"),
    ("modo", "Modo", "Case"),
    ("finsegun", "FinSegun", "EndSwitch"),
    ("mientras", "Mientras", "While"),
    ("finmientras", "FinMientras", "EndWhile"),
    ("repetir", "Repetir", "Repeat"),
    ("hasta", "Hasta", "Until"),
    ("que", "Que", "That"),
    ("para", "Para", "For"),
    ("con", "Con", "With"),
    ("paso", "Paso", "Step"),
    ("finpara", "FinPara", "EndFor"),
    ("entero", "Entero", "Integer"),
    ("real", "Real", "Real"),
    ("logico", "Lógico", "Boolean"),
    ("caracter", "Caracter", "Character"),
    ("cadena", "Cadena", "String"),
    ("verdadero", "Verdadero", "True"),
    ("falso", "Falso", "False"),
    ("y", "Y", "And"),
    ("o", "O", "Or"),
    ("no", "NO", "Not"),
    ("div", "DIV", "Div"),
    ("mod", "MOD", "Mod"),
)

SPANISH: dict[str, str] = {canonical: spanish for canonical, spanish, _english in _ROWS}
ENGLISH: dict[str, str] = {canonical: english for canonical, _spanish, english in _ROWS}
ALIASES: dict[str, str] = {
    canonicalize(english): canonical
    for canonical, _spanish, english in _ROWS
    if canonicalize(english) != canonical
}


def resolve_keyword(folded: str) -> str | None:
    """Devuelve el canónico español si el texto es palabra reservada en cualquier grafía."""
    if folded in KEYWORDS:
        return folded
    return ALIASES.get(folded)
