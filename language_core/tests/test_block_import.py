"""Un archivo de pseudocódigo vuelve a ser el mismo árbol de bloques."""

from language_core.ast_nodes import dump
from language_core.block_adapter import adapt_workspace
from language_core.block_import import workspace_from_source
from language_core.grammar import STRICT
from language_core.interpreter import compile_source


def _program(source: str):
    compiled = compile_source(source, STRICT)
    assert compiled.program is not None
    assert [item.code for item in compiled.diagnostics if item.severity == "error"] == []
    return compiled.program


def _round_trip(source: str) -> None:
    imported = workspace_from_source(source)
    assert imported.workspace is not None
    assert [item.severity for item in imported.diagnostics] == []
    adapted = adapt_workspace(imported.workspace)
    assert adapted.program is not None
    assert dump(adapted.program) == dump(_program(source))


def test_a_file_rebuilds_the_blocks_of_the_canvas() -> None:
    _round_trip(
        """
Algoritmo Laboratorio
    Definir n Como Entero;
    Definir i Como Entero;
    Definir texto Como Cadena;
    Definir letra Como Caracter;
    Definir ok Como Lógico;
    Definir precio Como Real;
    Leer n;
    n <- n + 2 * -3;
    texto <- "hola";
    letra <- 'a';
    ok <- Verdadero;
    precio <- 1.5;
    Si n > 0 Entonces
        Escribir n;
    Sino
        Escribir "no";
    FinSi
    Segun n Hacer
        1:
            Escribir "uno";
        2:
            Escribir "dos";
    De Otro Modo:
        Escribir "otro";
    FinSegun
    Mientras n < 3 Hacer
        n <- n + 1;
    FinMientras
    Para i <- 1 Hasta n Con Paso 1 Hacer
        Escribir i;
    FinPara
    Repetir
        n <- n - 1;
    Hasta Que n = 0
    Si ok Y NO Falso Entonces
        Escribir Concatenar(texto, "!");
    FinSi
FinAlgoritmo
"""
    )


def test_several_names_and_reads_become_one_block_each() -> None:
    imported = workspace_from_source(
        """
Algoritmo Laboratorio
    Definir a, b Como Entero;
    Leer a, b;
    a <- +1;
FinAlgoritmo
"""
    )
    assert imported.workspace is not None
    adapted = adapt_workspace(imported.workspace)
    assert adapted.program is not None
    text = dump(adapted.program)
    assert text.count("Define entero") == 2
    assert text.count("Read") == 2
    assert "Unary pos" not in text
    assert "Literal entero 1" in text


def test_a_for_without_step_gets_a_block_step() -> None:
    imported = workspace_from_source(
        """
Algoritmo Laboratorio
    Definir i Como Entero;
    Para i <- 3 Hasta 1 Hacer
        Escribir i;
    FinPara
FinAlgoritmo
"""
    )
    assert imported.workspace is not None
    assert imported.diagnostics[0].message == "Para: el archivo no traía paso. El bloque usa -1."
    adapted = adapt_workspace(imported.workspace)
    assert adapted.program is not None
    assert "step" in dump(adapted.program)
    assert "Literal entero 1" in dump(adapted.program)


def test_a_file_with_an_array_and_a_function_rebuilds_the_blocks() -> None:
    _round_trip(
        """
Funcion resultado <- Doblar(n)
    Definir resultado Como Entero;
    Definir n Como Entero;
    resultado <- n * 2;
FinFuncion
SubProceso Incrementar(edad Por Referencia)
    Definir edad Como Entero;
    edad <- edad + 1;
FinSubProceso
Algoritmo Laboratorio
    Definir datos Como Entero;
    Definir edad Como Entero;
    Dimension datos[2, 3] Como Entero;
    datos[1, 1] <- 8;
    Leer datos[1, 2];
    Escribir datos[1, 1];
    Escribir Doblar(3);
    edad <- 17;
    Incrementar(edad);
FinAlgoritmo
"""
    )


def test_borrar_and_esperar_rebuild_the_blocks() -> None:
    _round_trip(
        """
Algoritmo Laboratorio
    Escribir "Hola";
    Esperar 2 Segundos;
    Borrar Pantalla;
    Escribir "Listo";
FinAlgoritmo
"""
    )


def test_escribir_sin_saltar_rebuilds_the_blocks() -> None:
    _round_trip(
        """
Algoritmo Laboratorio
    Escribir "Hola " Sin Saltar;
    Escribir "mundo";
FinAlgoritmo
"""
    )


def test_escribir_with_several_values_rebuilds_the_blocks() -> None:
    _round_trip(
        """
Algoritmo Laboratorio
    Definir n Como Entero;
    Escribir "Le quedan ", n, " intentos:";
FinAlgoritmo
"""
    )


def test_a_guessing_game_without_semicolons_builds_the_canvas() -> None:
    imported = workspace_from_source(
        """
Algoritmo Adivina_Numero
 Definir intentos,num_secreto,num_ingresado como entero
    intentos<-10
    num_secreto <- Trunc(Aleatorio(0,100))

    Escribir "Adivine el numero (de 1 a 100):"
    Leer num_ingresado
    Mientras num_secreto<>num_ingresado Y intentos>1 Hacer
        Si num_secreto>num_ingresado Entonces
            Escribir "Muy bajo"
        Sino
            Escribir "Muy alto"
        FinSi
        intentos <- intentos-1
        Escribir "Le quedan ",intentos," intentos:"
        Leer num_ingresado
    FinMientras

    Si num_secreto=num_ingresado Entonces
        Escribir "Exacto! Usted adivino en ",11-intentos," intentos."
    Sino
        Escribir "El numero era: ",num_secreto
    FinSi

FinAlgoritmo
"""
    )
    assert imported.workspace is not None
    assert imported.diagnostics == ()
    adapted = adapt_workspace(imported.workspace)
    assert adapted.program is not None
    assert [item.severity for item in adapted.diagnostics] == []
    assert "Trunc(Aleatorio(0, 100))" in adapted.source
    assert 'Escribir "Le quedan ", intentos, " intentos:";' in adapted.source
    assert 'Escribir "Exacto! Usted adivino en ", 11 - intentos, " intentos.";' in adapted.source
    again = compile_source(adapted.source, STRICT)
    assert again.program is not None
    assert dump(again.program) == dump(adapted.program)


def test_power_does_not_build_a_canvas() -> None:
    power = workspace_from_source(
        "Algoritmo Laboratorio\nDefinir n Como Entero;\nn <- 2 ^ 3;\nFinAlgoritmo\n"
    )
    assert power.workspace is None
    assert "Potencia" in power.diagnostics[0].message


def test_a_broken_file_keeps_the_parser_message() -> None:
    imported = workspace_from_source("esto no es pseudocódigo")
    assert imported.workspace is None
    assert imported.diagnostics
    assert imported.diagnostics[0].severity == "error"


def test_an_empty_file_is_rejected() -> None:
    imported = workspace_from_source("   \n")
    assert imported.workspace is None
    assert imported.diagnostics[0].message == "El archivo está vacío."
