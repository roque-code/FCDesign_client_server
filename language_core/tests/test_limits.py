"""Pruebas de los límites de ejecución."""

from language_core.interpreter import execute_source
from language_core.runtime import Limits


def test_instruction_limit_points_at_loop() -> None:
    source = """
Algoritmo P
    Definir n Como Entero;
    n <- 1;
    Mientras n > 0 Hacer
        n <- n + 1;
    FinMientras
FinAlgoritmo
"""
    result = execute_source(source, limits=Limits(max_instructions=30))
    assert result.status == "error"
    error = result.diagnostics[-1]
    assert error.code == "E0410"
    assert error.span.start_line == 5
    assert "ciclo" in error.message


def test_time_limit() -> None:
    calls = {"n": 0}

    def clock() -> float:
        calls["n"] += 1
        return 0.0 if calls["n"] == 1 else 10.0

    result = execute_source(
        "Algoritmo P\nEscribir 1;\nFinAlgoritmo\n",
        limits=Limits(max_time_ms=1000),
        clock=clock,
    )
    assert result.status == "timeout"
    assert result.diagnostics[-1].code == "E0411"
    assert result.output == ""


def test_output_and_text_limits() -> None:
    long_text = execute_source(
        'Algoritmo P\nEscribir "hola";\nFinAlgoritmo\n',
        limits=Limits(max_string_length=3),
    )
    long_output = execute_source(
        'Algoritmo P\nEscribir "abcd";\nFinAlgoritmo\n',
        limits=Limits(max_output_chars=2),
    )
    assert long_text.diagnostics[-1].code == "E0413"
    assert long_output.diagnostics[-1].code == "E0414"
