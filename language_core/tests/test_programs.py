"""Algoritmos completos de la Fase 1."""

from pathlib import Path

from language_core.interpreter import execute_source

FIXTURES = Path(__file__).parent / "fixtures"


def _run(name: str, inputs: list[str] | None = None) -> str:
    source = (FIXTURES / name).read_text(encoding="utf-8")
    result = execute_source(source, inputs)
    assert result.status == "completed", result.diagnostics
    return result.output


def test_hola_mundo() -> None:
    assert _run("hola.traza") == "Hola mundo\n"


def test_area_de_un_triangulo() -> None:
    assert _run("area.traza", ["3", "4"]) == (
        "Ingrese la base:\n3\nIngrese la altura:\n4\nEl area es 6\n"
    )


def test_numero_mayor() -> None:
    assert _run("mayor.traza", ["4", "2"]) == "4\n2\n4\n"
    assert _run("mayor.traza", ["2", "9"]) == "2\n9\n9\n"
    assert _run("mayor.traza", ["3", "3"]) == "3\n3\niguales\n"


def test_tabla_de_multiplicar() -> None:
    lines = [f"2 x {i} = {2 * i}" for i in range(1, 11)]
    assert _run("tabla.traza", ["2"]) == "2\n" + "\n".join(lines) + "\n"


def test_promedio_de_calificaciones() -> None:
    assert _run("promedio.traza", ["0"]) == "0\nsin notas\n"
    assert _run("promedio.traza", ["3", "5", "5", "8"]) == "3\n5\n5\n8\n6\n"


def test_ejemplo_de_edad() -> None:
    mayor = _run("ejemplo.traza", ["Ana", "18"])
    menor = _run("ejemplo.traza", ["Ana", "17"])
    assert mayor == "Ingrese su nombre:\nAna\nIngrese su edad:\n18\nAna es mayor de edad\n"
    assert menor == "Ingrese su nombre:\nAna\nIngrese su edad:\n17\nAna es menor de edad\n"
