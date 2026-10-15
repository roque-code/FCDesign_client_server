"""Pruebas del analizador semántico."""

from language_core.grammar import FLEXIBLE, LanguageProfile
from language_core.interpreter import compile_source


def codes(source: str, profile=None) -> list[str]:
    return [item.code for item in compile_source(source, profile).diagnostics]


def test_undeclared_duplicate_and_reserved() -> None:
    source = """
Algoritmo X
    Definir edad Como Entero;
    Definir edad Como Real;
    Definir Abs Como Entero;
    Escribir peso;
FinAlgoritmo
"""
    found = codes(source)
    assert "E0302" in found
    assert "E0307" in found
    assert "E0301" in found


def test_incompatible_assignment_and_condition() -> None:
    source = """
Algoritmo X
    Definir n Como Entero;
    Definir texto Como Cadena;
    n <- 3.5;
    texto <- 1 + "a";
    Si 1 Entonces
        Escribir n;
    FinSi
FinAlgoritmo
"""
    found = codes(source)
    assert "E0303" in found
    assert "E0305" in found
    assert "E0304" in found


def test_real_equality_warning_and_unused_variable() -> None:
    source = """
Algoritmo X
    Definir r Como Real;
    Definir extra Como Entero;
    r <- 1.5;
    Escribir r = 1.5;
FinAlgoritmo
"""
    found = codes(source)
    assert "W0501" in found
    assert "W0503" in found
    quiet = codes(source, LanguageProfile(name="quiet", beginner_warnings=False))
    assert "W0501" not in quiet
    assert "W0503" not in quiet


def test_for_variable_must_be_integer() -> None:
    source = """
Algoritmo X
    Definir i Como Real;
    Para i <- 1 Hasta 3 Hacer
        Escribir 1;
    FinPara
FinAlgoritmo
"""
    assert "E0308" in codes(source)


def test_negative_power_is_real() -> None:
    source = """
Algoritmo X
    Definir n Como Entero;
    n <- 2 ^ -1;
FinAlgoritmo
"""
    assert "E0303" in codes(source)


def test_missing_return_is_reported() -> None:
    source = """
Funcion r <- F()
    Definir r Como Entero;
FinFuncion
Algoritmo X
    Escribir F();
FinAlgoritmo
"""
    assert "E0309" in codes(source)


def test_definition_inside_if_is_visible_later() -> None:
    source = """
Algoritmo X
    Definir c Como Logico;
    c <- Falso;
    Si c Entonces
        Definir x Como Entero;
    FinSi
    x <- 4;
    Escribir x;
FinAlgoritmo
"""
    assert codes(source) == []


def test_flexible_profile_infers_assignment() -> None:
    source = "Algoritmo X\nn <- 1\nEscribir n\nFinAlgoritmo\n"
    assert codes(source, FLEXIBLE) == []


def test_comparisons_of_different_types() -> None:
    source = """
Algoritmo X
    Definir n Como Entero;
    Definir s Como Cadena;
    n <- 1;
    s <- "a";
    Escribir n = s;
FinAlgoritmo
"""
    assert "E0306" in codes(source)


def test_unary_and_logic_comparison_rules() -> None:
    signed = """
Algoritmo X
    Escribir NO 1;
    Escribir -"a";
FinAlgoritmo
"""
    logic = """
Algoritmo X
    Definir a, b Como Logico;
    Definir c Como Caracter;
    a <- Verdadero;
    b <- Falso;
    c <- "AB";
    Escribir a < b;
FinAlgoritmo
"""
    reserved = """
Algoritmo X
    Definir n Como Entero;
    Abs <- 1;
    Escribir n;
FinAlgoritmo
"""
    assert "E0305" in codes(signed)
    assert "E0306" in codes(logic)
    assert "E0303" in codes(logic)
    assert "E0307" in codes(reserved)


def test_divmod_require_integers() -> None:
    source = """
Algoritmo X
    Definir r Como Real;
    r <- 4.0;
    Escribir r DIV 2;
FinAlgoritmo
"""
    assert "E0305" in codes(source)
