"""Pruebas del analizador sintáctico y del volcado del AST."""

from language_core.ast_nodes import dump
from language_core.grammar import FLEXIBLE, STRICT
from language_core.lexer import lex
from language_core.parser import parse


def _program(source: str, profile=STRICT):
    lexed = lex(source)
    return parse(lexed.tokens, source, profile)


def test_dump_of_conditional() -> None:
    source = """
Algoritmo Mayor
    Definir a, b Como Entero;
    Leer a;
    Leer b;
    Si a > b Entonces
        Escribir a;
    Sino
        Escribir b;
    FinSi
FinAlgoritmo
"""
    program, diagnostics = _program(source)
    assert diagnostics == ()
    assert program is not None
    assert dump(program) == "\n".join(
        [
            "Program Mayor",
            "  Algorithm Mayor",
            "    Define entero a, b",
            "    Read",
            "      LValue a",
            "    Read",
            "      LValue b",
            "    If",
            "      Binary gt",
            "        Name a",
            "        Name b",
            "    then",
            "      Write",
            "        Name a",
            "    else",
            "      Write",
            "        Name b",
        ]
    )


def test_power_and_unary_shape() -> None:
    source = """
Algoritmo P
    Definir r Como Entero;
    r <- -2^2;
FinAlgoritmo
"""
    program, diagnostics = _program(source)
    assert diagnostics == ()
    assert program is not None
    text = dump(program)
    assert "Unary neg" in text
    assert text.index("Unary neg") < text.index("Binary pow")


def test_missing_finsi_points_at_si() -> None:
    source = "Algoritmo X\n    Si Verdadero Entonces\n        Escribir 1;\nFinAlgoritmo\n"
    _program_tree, diagnostics = _program(source)
    error = next(item for item in diagnostics if item.code == "E0202")
    assert error.span.start_line == 2
    assert error.span.start_col == 5
    assert "FinSi" in error.message
    assert error.suggestion
    assert "Si Verdadero" in error.snippet


def test_missing_finmientras_and_finpara() -> None:
    while_source = "Algoritmo X\nMientras Verdadero Hacer\nEscribir 1;\nFinAlgoritmo\n"
    for_source = "Algoritmo X\nDefinir i Como Entero;\nPara i <- 1 Hasta 2 Hacer\nEscribir i;\nFinAlgoritmo\n"
    while_diags = _program(while_source)[1]
    for_diags = _program(for_source)[1]
    assert any(item.code == "E0202" and "FinMientras" in item.message for item in while_diags)
    assert any(item.code == "E0202" and "FinPara" in item.message for item in for_diags)


def test_semicolon_rules() -> None:
    missing = "Algoritmo X\nEscribir 1\nFinAlgoritmo\n"
    extra = "Algoritmo X\nEscribir 1;;\nFinAlgoritmo\n"
    assert any(item.code == "E0210" for item in _program(missing)[1])
    assert any(item.code == "E0211" for item in _program(extra)[1])
    flexible = _program(missing, FLEXIBLE)[1]
    assert not any(item.code == "E0210" for item in flexible)


def test_equals_is_not_assignment_in_strict_profile() -> None:
    source = "Algoritmo X\nDefinir n Como Entero;\nn = 1;\nFinAlgoritmo\n"
    strict = _program(source)[1]
    flexible = _program(source, FLEXIBLE)[1]
    assert any(item.code == "E0203" for item in strict)
    assert not any(item.code == "E0203" for item in flexible)


def test_chained_comparison_is_rejected() -> None:
    source = "Algoritmo X\nDefinir a Como Entero;\na <- 1;\nEscribir a < 2 < 3;\nFinAlgoritmo\n"
    diagnostics = _program(source)[1]
    error = next(item for item in diagnostics if item.code == "E0204")
    assert "Y" in (error.suggestion or "")


def test_subroutines_and_switch_are_parsed() -> None:
    source = """
Funcion resultado <- Sumar(a, b Por Referencia)
    Definir resultado Como Entero;
    resultado <- a;
FinFuncion
Algoritmo X
    Segun 1 Hacer
        1:
            Escribir 1;
        2, 3:
            Escribir 2;
        De Otro Modo:
            Escribir 0;
    FinSegun
FinAlgoritmo
SubProceso Mostrar(nombre)
    Escribir nombre;
FinSubProceso
"""
    program, diagnostics = _program(source)
    assert program is not None
    assert diagnostics == ()
    text = dump(program)
    assert "Function resultado <- Sumar(a:value, b:reference)" in text
    assert "Procedure Mostrar(nombre:value)" in text
    assert "Switch" in text
    assert "default" in text


def test_unclosed_parenthesis_and_empty_file() -> None:
    paren = _program("Algoritmo X\nEscribir (1;\nFinAlgoritmo\n")[1]
    empty = _program("")[1]
    assert any(item.code == "E0212" for item in paren)
    assert any(item.code == "E0205" for item in empty)


def test_two_algorithms() -> None:
    source = "Algoritmo A\nFinAlgoritmo\nAlgoritmo B\nFinAlgoritmo\n"
    diagnostics = _program(source)[1]
    assert any(item.code == "E0311" for item in diagnostics)


def test_dump_covers_remaining_nodes() -> None:
    source = """
Funcion resultado <- Doblar(n)
    Definir resultado Como Entero;
    resultado <- n;
FinFuncion
Algoritmo Completo
    Definir i Como Entero;
    Dimension matriz[2, 3] Como Entero;
    matriz[1, 2] <- 4;
    Leer matriz[1];
    Escribir matriz[1];
    Escribir Doblar(i);
    Doblar(i);
    Mientras Verdadero Hacer
        Escribir 1;
    FinMientras
    Repetir
        Escribir 2;
    Hasta Que Falso
    Para i <- 1 Hasta 2 Con Paso 1 Hacer
        Escribir i;
    FinPara
FinAlgoritmo
"""
    program, _diagnostics = _program(source)
    assert program is not None
    text = dump(program)
    for label in (
        "Dimension",
        "Dim matriz entero",
        "Call Doblar",
        "CallStmt",
        "Index matriz",
        "While",
        "Repeat",
        "until",
        "For i",
        "step",
    ):
        assert label in text


def test_syntax_errors_are_localized() -> None:
    samples = [
        "Funcion\nFinFuncion\nAlgoritmo A\nFinAlgoritmo\n",
        "Algoritmo\nFinAlgoritmo\n",
        "Algoritmo A\nDefinir Como Entero;\nFinAlgoritmo\n",
        "Algoritmo A\nDefinir a, Como Entero;\nFinAlgoritmo\n",
        "Algoritmo A\nDefinir a Entero;\nFinAlgoritmo\n",
        "Algoritmo A\nDefinir a Como ;\nFinAlgoritmo\n",
        "Algoritmo A\nDimension ;\nFinAlgoritmo\n",
        "Algoritmo A\nDimension v ;\nFinAlgoritmo\n",
        "Algoritmo A\nDimension v[1;\nFinAlgoritmo\n",
        "Algoritmo A\nLeer ;\nFinAlgoritmo\n",
        "Algoritmo A\nDefinir a Como Entero;\na;\nFinAlgoritmo\n",
        "Algoritmo A\nSi Entonces\nFinSi\nFinAlgoritmo\n",
        "Algoritmo A\nSegun\nFinSegun\nFinAlgoritmo\n",
        "Algoritmo A\nMientras Hacer\nFinMientras\nFinAlgoritmo\n",
        "Algoritmo A\nRepetir\nHasta\nFinAlgoritmo\n",
        "Algoritmo A\nDefinir i Como Entero;\nPara Hasta 1 Hacer\nFinPara\nFinAlgoritmo\n",
        "Algoritmo A\nDefinir i Como Entero;\nPara i <- 1 Hacer\nFinPara\nFinAlgoritmo\n",
        "Algoritmo A\nDefinir i Como Entero;\nPara i <- 1 Hasta 2 Con Hacer\nFinPara\nFinAlgoritmo\n",
        "Algoritmo A\nDefinir i Como Entero;\nPara i <- 1 Hasta 2\nFinPara\nFinAlgoritmo\n",
        "Algoritmo A\nEscribir (1;\nFinAlgoritmo\n",
        "Algoritmo A\nDefinir a Como Entero;\na[1 <- 2;\nFinAlgoritmo\n",
        "Algoritmo A\nEscribir 1 + ;\nFinAlgoritmo\n",
        "SubProceso\nFinSubProceso\nAlgoritmo A\nFinAlgoritmo\n",
        "Algoritmo A\nFuncion r <- F()\nFinFuncion\nFinAlgoritmo\n",
        "Algoritmo A\nSubProceso P()\nFinSubProceso\nFinAlgoritmo\n",
        "???\n",
    ]
    for source in samples:
        _tree, diagnostics = _program(source)
        assert diagnostics, source


def test_missing_repeat_closer() -> None:
    source = "Algoritmo X\nRepetir\nEscribir 1;\nFinAlgoritmo\n"
    diagnostics = _program(source)[1]
    assert any(item.code == "E0202" and "Hasta Que" in item.message for item in diagnostics)


def test_english_keywords_build_the_same_tree() -> None:
    spanish = """
Algoritmo Demo
    Definir n Como Entero;
    n <- 0;
    Repetir
        n <- n + 1;
    Hasta Que n > 1
    Segun n Hacer
        1:
            Escribir 1;
        De Otro Modo:
            Escribir 0;
    FinSegun
    Si Verdadero Y n > 0 Entonces
        Escribir n;
    Sino
        Escribir 0;
    FinSi
FinAlgoritmo
"""
    english = """
Algorithm Demo
    Declare n As Integer;
    n <- 0;
    Repeat
        n <- n + 1;
    Until That n > 1
    Switch n Do
        1:
            Write 1;
        In Other Case:
            Write 0;
    EndSwitch
    If True And n > 0 Then
        Write n;
    Else
        Write 0;
    EndIf
EndAlgorithm
"""
    left, left_notes = _program(spanish)
    right, right_notes = _program(english)
    assert left_notes == ()
    assert right_notes == ()
    assert left is not None and right is not None

    def same(text: str) -> str:
        return text.replace("Verdadero", "True").replace("Falso", "False")

    assert same(dump(left)) == same(dump(right))
