"""Pruebas de ejecución, entrada y operadores."""

from language_core.grammar import LanguageProfile
from language_core.interpreter import execute_source
from language_core.runtime import Cancellation


def run(source: str, inputs: list[str] | None = None, **kwargs):
    return execute_source(source, inputs, **kwargs)


def test_arithmetic_precedence_and_division() -> None:
    source = """
Algoritmo P
    Definir n Como Entero;
    Definir r Como Real;
    n <- -2^2;
    Escribir n;
    n <- 2^3^2;
    Escribir n;
    Escribir -7 DIV 2;
    Escribir -7 MOD 2;
    Escribir -7 % 2;
    r <- 1 / 4;
    Escribir r;
    Escribir NO Falso Y Falso;
    Escribir Verdadero O Falso Y Falso;
FinAlgoritmo
"""
    result = run(source)
    assert result.status == "completed"
    assert result.output == "-4\n512\n-3\n-1\n-1\n0.25\nFalso\nVerdadero\n"


def test_short_circuit_skips_unassigned_operand() -> None:
    source = """
Algoritmo P
    Definir a, b Como Logico;
    a <- Falso;
    Escribir a Y b;
    a <- Verdadero;
    Escribir a O b;
FinAlgoritmo
"""
    result = run(source)
    assert result.status == "completed"
    assert result.output == "Falso\nVerdadero\n"


def test_short_circuit_evaluates_when_needed() -> None:
    source = """
Algoritmo P
    Definir a, b Como Logico;
    a <- Verdadero;
    Escribir a Y b;
FinAlgoritmo
"""
    result = run(source)
    assert result.status == "error"
    assert result.diagnostics[-1].code == "E0401"


def test_unassigned_scalar_and_division_by_zero() -> None:
    missing = run("Algoritmo P\nDefinir x Como Entero;\nEscribir x;\nFinAlgoritmo\n")
    zero = run("Algoritmo P\nEscribir 1 / 0;\nFinAlgoritmo\n")
    power = run("Algoritmo P\nEscribir 0^0;\nFinAlgoritmo\n")
    assert missing.diagnostics[-1].code == "E0401"
    assert zero.diagnostics[-1].code == "E0402"
    assert power.diagnostics[-1].code == "E0403"


def test_invalid_power_of_negative_base() -> None:
    result = run("Algoritmo P\nEscribir (-8) ^ 0.5;\nFinAlgoritmo\n")
    assert result.diagnostics[-1].code == "E0403"


def test_read_retries_invalid_input() -> None:
    source = """
Algoritmo P
    Definir edad Como Entero;
    Definir nombre Como Cadena;
    Definir activo Como Logico;
    Definir inicial Como Caracter;
    Leer edad;
    Leer nombre;
    Leer activo;
    Leer inicial;
    Escribir nombre, " ", edad, " ", activo, " ", inicial;
FinAlgoritmo
"""
    result = run(source, ["xx", "18", " Ana", "VERDADERO", "Z"])
    assert result.status == "completed"
    assert any(item.code == "E0406" for item in result.diagnostics)
    assert result.output == "18\n Ana\nVERDADERO\nZ\n Ana 18 Verdadero Z\n"
    assert result.variables["edad"] == "18"


def test_el_dato_aceptado_queda_en_la_consola() -> None:
    source = """
Algoritmo P
    Definir n Como Entero;
    Escribir "n:";
    Leer n;
    Escribir n * 2;
FinAlgoritmo
"""
    result = run(source, ["no", "6"])
    assert result.status == "completed"
    assert result.output == "n:\n6\n12\n"


def test_read_waits_when_no_input_remains() -> None:
    result = run("Algoritmo P\nDefinir n Como Entero;\nLeer n;\nFinAlgoritmo\n", [])
    assert result.status == "waiting_input"
    assert result.pending_input == {"name": "n", "type": "entero"}


def test_if_while_repeat_and_for() -> None:
    source = """
Algoritmo P
    Definir n, i Como Entero;
    n <- 0;
    Si n = 0 Entonces
        Escribir "cero";
    Sino
        Escribir "otro";
    FinSi
    Mientras n < 2 Hacer
        n <- n + 1;
    FinMientras
    Escribir n;
    Repetir
        n <- n + 1;
    Hasta Que n = 4
    Escribir n;
    Para i <- 1 Hasta 3 Hacer
        Escribir i;
    FinPara
    Para i <- 3 Hasta 1 Hacer
        Escribir i;
    FinPara
FinAlgoritmo
"""
    result = run(source)
    assert result.status == "completed"
    assert result.output == "cero\n2\n4\n1\n2\n3\n3\n2\n1\n"


def test_omitted_step_and_explicit_step_that_does_not_enter() -> None:
    down = run("""
Algoritmo P
    Definir i Como Entero;
    Para i <- 1 Hasta 0 Hacer
        Escribir i;
    FinPara
FinAlgoritmo
""")
    stopped = run("""
Algoritmo P
    Definir i Como Entero;
    Para i <- 10 Hasta 1 Con Paso 1 Hacer
        Escribir i;
    FinPara
FinAlgoritmo
""")
    zero = run("""
Algoritmo P
    Definir i Como Entero;
    Para i <- 1 Hasta 3 Con Paso 0 Hacer
        Escribir i;
    FinPara
FinAlgoritmo
""")
    assert down.output == "1\n0\n"
    assert stopped.status == "completed"
    assert stopped.output == ""
    assert any(item.code == "W0502" for item in stopped.diagnostics)
    assert stopped.variables["i"] == "10"
    assert zero.diagnostics[-1].code == "E0405"


def test_definition_is_hoisted_and_not_reset() -> None:
    hoisted = run("""
Algoritmo P
    Definir c Como Logico;
    c <- Falso;
    Si c Entonces
        Definir x Como Entero;
    FinSi
    x <- 4;
    Escribir x;
FinAlgoritmo
""")
    kept = run("""
Algoritmo P
    Definir n, x Como Entero;
    n <- 0;
    x <- 0;
    Mientras n < 2 Hacer
        Definir extra Como Entero;
        n <- n + 1;
        x <- x + 1;
    FinMientras
    Escribir x;
FinAlgoritmo
""")
    assert hoisted.output == "4\n"
    assert kept.output == "2\n"


def test_real_literal_is_exact_and_widens() -> None:
    result = run("""
Algoritmo P
    Definir r Como Real;
    r <- 9.5;
    Escribir r;
    r <- 3;
    Escribir r;
FinAlgoritmo
""")
    assert result.output == "9.5\n3\n"


def test_widening_can_be_disabled() -> None:
    profile = LanguageProfile(name="narrow", implicit_widening=False, beginner_warnings=False)
    result = run(
        "Algoritmo P\nDefinir r Como Real;\nr <- 3;\nFinAlgoritmo\n",
        profile=profile,
    )
    assert result.status == "error"
    assert any(item.code == "E0303" for item in result.diagnostics)


def test_cancel_before_running() -> None:
    cancellation = Cancellation()
    cancellation.cancel()
    result = run(
        "Algoritmo P\nEscribir 1;\nFinAlgoritmo\n",
        cancellation=cancellation,
    )
    assert result.status == "cancelled"
    assert result.diagnostics[-1].code == "E0416"
    assert result.output == ""


def test_syntax_error_does_not_execute() -> None:
    result = run("Algoritmo P\nEscribir 1\nFinAlgoritmo\n")
    assert result.status == "error"
    assert result.output == ""
    assert any(item.code == "E0210" for item in result.diagnostics)


def test_more_operators_and_coercions() -> None:
    source = """
Algoritmo P
    Definir s Como Cadena;
    Definir c Como Caracter;
    Definir r Como Real;
    s <- "b";
    c <- "A";
    r <- +1.5;
    Escribir s > "a";
    Escribir c;
    Escribir r;
    Escribir +2;
    Escribir 9.5 - 1.5;
    Escribir 2 * 1.5;
    Escribir Verdadero <> Falso;
    s <- "AB";
    c <- s;
FinAlgoritmo
"""
    result = run(source)
    assert result.diagnostics[-1].code == "E0303"
    assert "Verdadero" in result.output
    assert "A\n" in result.output


def test_integer_division_by_zero_and_huge_power() -> None:
    divided = run("Algoritmo P\nEscribir 1 DIV 0;\nFinAlgoritmo\n")
    remainder = run("Algoritmo P\nEscribir 1 MOD 0;\nFinAlgoritmo\n")
    huge = run("Algoritmo P\nEscribir 2^10001;\nFinAlgoritmo\n")
    assert divided.diagnostics[-1].code == "E0402"
    assert remainder.diagnostics[-1].code == "E0402"
    assert huge.diagnostics[-1].code == "E0413"


def test_while_can_skip_its_body() -> None:
    result = run("""
Algoritmo P
    Definir n Como Entero;
    n <- 0;
    Mientras n > 0 Hacer
        Escribir 1;
    FinMientras
    Escribir "fin";
FinAlgoritmo
""")
    assert result.output == "fin\n"


def test_flexible_for_and_read() -> None:
    from language_core.grammar import FLEXIBLE

    result = run(
        "Algoritmo P\nLeer nombre\nEscribir nombre\nPara i <- 1 Hasta 2 Hacer\nEscribir i\nFinPara\nFinAlgoritmo\n",
        ["Ana"],
        profile=FLEXIBLE,
    )
    assert result.status == "completed"
    assert result.output == "Ana\nAna\n1\n2\n"


def test_borrar_pantalla_keeps_only_the_later_text() -> None:
    result = run("""
Algoritmo P
    Escribir "Hola";
    Borrar Pantalla;
    Escribir "Listo";
FinAlgoritmo
""")
    assert result.status == "completed"
    assert result.output == "Listo\n"


def test_esperar_pauses_and_then_clears(monkeypatch) -> None:
    paused: list[float] = []
    monkeypatch.setattr(
        "language_core.debugger.pause_for",
        lambda seconds, cancellation=None: paused.append(seconds),
    )
    result = run("""
Algoritmo P
    Escribir "Hola";
    Esperar 2 Segundos;
    Borrar Pantalla;
    Escribir "Listo";
FinAlgoritmo
""")
    assert result.status == "completed"
    assert paused == [2]
    assert result.output == "Listo\n"


def test_esperar_rejects_text_and_a_long_wait() -> None:
    text = run("""
Algoritmo P
    Esperar "hola" Segundos;
FinAlgoritmo
""")
    assert text.status == "error"
    assert text.diagnostics[0].code == "E0303"
    long = run("""
Algoritmo P
    Esperar 61 Segundos;
FinAlgoritmo
""")
    assert long.status == "error"
    assert long.diagnostics[0].code == "E0417"


def test_escribir_sin_saltar_stays_on_the_same_line() -> None:
    result = run("""
Algoritmo P
    Escribir "Hola " Sin Saltar;
    Escribir "mundo";
    Escribir "x" Sin Saltar;
FinAlgoritmo
""")
    assert result.status == "completed"
    assert result.output == "Hola mundo\nx"


def test_less_than_negative_literal() -> None:
    result = run("""
Algoritmo P
    Definir a Como Entero;
    a <- 1;
    Escribir a < -1;
FinAlgoritmo
""")
    assert result.output == "Falso\n"
