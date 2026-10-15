"""Arreglos, Segun, subrutinas y biblioteca estándar."""

import random
from pathlib import Path

from language_core.flowchart import build
from language_core.grammar import FLEXIBLE, LanguageProfile
from language_core.interpreter import compile_source, execute_source

FIXTURES = Path(__file__).parent / "fixtures"


def _output(name: str, inputs: list[str] | None = None) -> str:
    source = (FIXTURES / name).read_text(encoding="utf-8")
    result = execute_source(source, inputs)
    assert result.status == "completed", result.diagnostics
    return result.output


def _codes(source: str, profile: LanguageProfile | None = None) -> list[str]:
    return [item.code for item in compile_source(source, profile).diagnostics]


def test_factorial_iterativo() -> None:
    assert _output("factorial.traza", ["5"]) == "5\n120\n"
    assert _output("factorial.traza", ["1"]) == "1\n1\n"


def test_arreglo_unidimensional() -> None:
    assert _output("arreglo.traza") == "150\n"


def test_matriz() -> None:
    assert _output("matriz.traza") == "102\n"


def test_busqueda_lineal() -> None:
    assert _output("busqueda.traza", ["9"]) == "9\n3\n"
    assert _output("busqueda.traza", ["5"]) == "5\n0\n"


def test_ordenamiento() -> None:
    assert _output("ordenar.traza") == "1\n2\n3\n4\n"


def test_funcion_con_parametros() -> None:
    assert _output("doblar.traza", ["21"]) == "21\n42\n"


def test_procedimiento_por_referencia() -> None:
    assert _output("procedimiento.traza") == "18\n"


def test_factorial_recursivo() -> None:
    assert _output("recursivo.traza", ["5"]) == "5\n120\n"


def test_arreglo_de_tres_dimensiones_y_fuera_de_rango() -> None:
    source = """
Algoritmo Cubo
    Definir cubo, suma Como Entero;
    Dimension cubo[2, 2, 2] Como Entero;
    cubo[1, 2, 2] <- 8;
    suma <- cubo[1, 1, 1] + cubo[1, 2, 2];
    Escribir suma;
    Escribir cubo[0, 1, 1];
FinAlgoritmo
"""
    result = execute_source(source)
    assert result.status == "error"
    assert result.diagnostics[-1].code == "E0404"
    assert "0" in result.diagnostics[-1].message


def test_base_cero() -> None:
    profile = LanguageProfile(name="zero", index_base=0)
    source = """
Algoritmo Base
    Definir datos Como Entero;
    Dimension datos[2] Como Entero;
    datos[0] <- 5;
    datos[1] <- 6;
    Escribir datos[0];
FinAlgoritmo
"""
    result = execute_source(source, profile=profile)
    assert result.status == "completed", result.diagnostics
    assert result.output == "5\n"
    outside = execute_source(
        source.replace("Escribir datos[0];", "Escribir datos[2];"), profile=profile
    )
    assert outside.diagnostics[-1].code == "E0404"


def test_arreglo_por_valor_no_cambia_el_original() -> None:
    source = """
SubProceso Tocar(v Por Valor)
    Definir v Como Entero;
    Dimension v[1];
    v[1] <- 9;
FinSubProceso
Algoritmo Copia
    Definir datos Como Entero;
    Dimension datos[1] Como Entero;
    datos[1] <- 1;
    Tocar(datos);
    Escribir datos[1];
FinAlgoritmo
"""
    result = execute_source(source)
    assert result.status == "completed", result.diagnostics
    assert result.output == "1\n"


def test_arreglo_por_referencia() -> None:
    source = """
SubProceso Tocar(v)
    Definir v Como Entero;
    Dimension v[1];
    v[1] <- 9;
FinSubProceso
Algoritmo Original
    Definir datos Como Entero;
    Dimension datos[1] Como Entero;
    datos[1] <- 1;
    Tocar(datos);
    Escribir datos[1];
FinAlgoritmo
"""
    result = execute_source(source)
    assert result.status == "completed", result.diagnostics
    assert result.output == "9\n"


def test_segun_elige_un_caso_sin_caer_al_siguiente() -> None:
    source = """
Algoritmo Seleccion
    Definir opcion Como Entero;
    Leer opcion;
    Segun opcion Hacer
        1:
            Escribir "uno";
        2, 3:
            Escribir "varios";
        De Otro Modo:
            Escribir "otro";
    FinSegun
FinAlgoritmo
"""
    assert execute_source(source, ["1"]).output == "1\nuno\n"
    assert execute_source(source, ["3"]).output == "3\nvarios\n"
    assert execute_source(source, ["8"]).output == "8\notro\n"


def test_etiqueta_de_segun_debe_ser_literal_y_no_repetirse() -> None:
    repeated = """
Algoritmo X
    Segun 1 Hacer
        1:
            Escribir 1;
        1:
            Escribir 2;
    FinSegun
FinAlgoritmo
"""
    expression = """
Algoritmo X
    Segun 1 Hacer
        1 + 0:
            Escribir 1;
    FinSegun
FinAlgoritmo
"""
    assert "E0316" in _codes(repeated)
    assert "E0315" in _codes(expression)


def test_segun_compara_etiquetas_negativas() -> None:
    source = """
Algoritmo Seleccion
    Definir estado Como Entero;
    Leer estado;
    Segun estado Hacer
        0:
            Escribir "cero";
        -1, -5:
            Escribir "bajo";
        -3:
            Escribir "tres";
        De Otro Modo:
            Escribir "otro";
    FinSegun
FinAlgoritmo
"""
    assert execute_source(source, ["-1"]).output == "-1\nbajo\n"
    assert execute_source(source, ["-5"]).output == "-5\nbajo\n"
    assert execute_source(source, ["-3"]).output == "-3\ntres\n"
    assert execute_source(source, ["0"]).output == "0\ncero\n"
    real = """
Algoritmo Seleccion
    Definir estado Como Real;
    estado <- -1.5;
    Segun estado Hacer
        -1.5:
            Escribir "real";
    FinSegun
FinAlgoritmo
"""
    assert execute_source(real).output == "real\n"
    repeated = """
Algoritmo X
    Segun 1 Hacer
        -1:
            Escribir 1;
        -1:
            Escribir 2;
    FinSegun
FinAlgoritmo
"""
    assert "E0316" in _codes(repeated)
    loose = """
Algoritmo P
    Definir estado Como Entero
    estado <- -1
    Segun estado Hacer
        0: estado <- 0
        -1, -5: estado <- 8
    FinSegun
    Escribir estado
FinAlgoritmo
"""
    compiled = compile_source(loose, FLEXIBLE)
    assert compiled.program is not None
    assert [item.code for item in compiled.diagnostics if item.severity == "error"] == []
    labels = [edge.label for edge in build(compiled.program).edges]
    assert "-1, -5" in labels
    assert execute_source(loose, profile=FLEXIBLE).output == "8\n"


def test_aridad_retorno_ausente_y_profundidad() -> None:
    missing = """
Funcion r <- F()
    Definir r Como Entero;
FinFuncion
Algoritmo X
    Escribir F();
FinAlgoritmo
"""
    arity = """
Funcion r <- Doblar(n)
    Definir r, n Como Entero;
    r <- n;
FinFuncion
Algoritmo X
    Escribir Doblar();
FinAlgoritmo
"""
    assert "E0309" in _codes(missing)
    assert "E0311" in _codes(arity)
    deep = LanguageProfile(name="shallow", max_call_depth=2)
    result = execute_source((FIXTURES / "recursivo.traza").read_text(encoding="utf-8"), ["5"], deep)
    assert result.status == "error"
    assert result.diagnostics[-1].code == "E0412"


def test_biblioteca_y_perfil_flexible() -> None:
    source = """
Algoritmo Libros
    Definir texto Como Cadena;
    texto <- "Hola";
    Escribir Abs(-5);
    Escribir Raiz(9);
    Escribir Redon(2.5);
    Escribir Trunc(-3.9);
    Escribir Sen(0);
    Escribir Longitud(texto);
    Escribir SubCadena(texto, 2, 4);
    Escribir Mayusculas("ab");
    Escribir Concatenar("a", 1);
    Escribir ConvertirANumero("18");
    Escribir Aleatorio(4, 4);
FinAlgoritmo
"""
    result = execute_source(source, rng=random.Random(0))
    assert result.status == "completed", result.diagnostics
    assert result.output == "5\n3\n3\n-3\n0\n4\nola\nAB\na1\n18\n4\n"
    flexible = """
Algoritmo Flex
Dimension datos[2]
datos[1] <- 4
Escribir datos[1]
FinAlgoritmo
"""
    done = execute_source(flexible, profile=FLEXIBLE)
    assert done.status == "completed", done.diagnostics
    assert done.output == "4\n"
    assert "E0314" in _codes("Algoritmo X\nDimension datos[2];\nFinAlgoritmo\n")


def test_mas_funciones_de_biblioteca() -> None:
    source = """
Algoritmo Mas
    Escribir Potencia(2, 3);
    Escribir Cos(0);
    Escribir Exp(0);
    Escribir Ln(1);
    Escribir Minusculas("Ab");
    Escribir ConvertirATexto(Verdadero);
    Escribir Tan(0);
FinAlgoritmo
"""
    result = execute_source(source)
    assert result.status == "completed", result.diagnostics
    assert result.output.splitlines()[0] == "8"
    bad = execute_source("Algoritmo X\nEscribir Ln(0);\nFinAlgoritmo\n")
    assert bad.diagnostics[-1].code == "E0403"
    text = execute_source('Algoritmo X\nEscribir ConvertirANumero("no");\nFinAlgoritmo\n')
    assert text.diagnostics[-1].code == "E0407"
    missing = _codes("Algoritmo X\nEscribir NoExiste(1);\nFinAlgoritmo\n")
    assert "E0310" in missing
    root = execute_source("Algoritmo X\nEscribir Raiz(-1);\nFinAlgoritmo\n")
    assert root.diagnostics[-1].code == "E0403"
    huge = LanguageProfile(name="tiny", max_array_cells=3)
    result = execute_source(
        "Algoritmo X\nDefinir a Como Entero;\nDimension a[4] Como Entero;\nFinAlgoritmo\n",
        profile=huge,
    )
    assert result.diagnostics[-1].code == "E0413"
