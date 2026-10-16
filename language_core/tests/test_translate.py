"""La traducción conserva el resultado del intérprete y los comentarios."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from language_core.grammar import LanguageProfile
from language_core.interpreter import execute_source
from language_core.lexer import lex
from language_core.translate import TARGETS, translate_source

FIXTURES = Path(__file__).parent / "fixtures"

SINK = """
// presentación
Algoritmo Cocina
    Definir n, i, suma, bandera Como Entero;
    Definir texto Como Cadena;
    Definir activo Como Logico;
    Dimension numeros[3] Como Entero;
    Leer n;
    suma <- 0;
    Si n > 0 Entonces
        Para i <- 1 Hasta 3 Hacer
            numeros[i] <- i * n;
            suma <- suma + numeros[i];
        FinPara
    Sino
        suma <- -7 DIV 2;
    FinSi
    Repetir
        suma <- suma + 1;
    Hasta Que suma > 0
    Segun suma Hacer
        1: Escribir "uno";
        2, 3: Escribir "varios";
    De Otro Modo:
        Escribir suma;
    FinSegun
    activo <- Verdadero;
    Escribir activo;
    texto <- "Ab";
    Escribir SubCadena(texto, 1, 1), Longitud(texto);
    Escribir Abs(-4);
    Borrar Pantalla;
    Escribir "fin" Sin Saltar;
FinAlgoritmo
"""


def _python(source: str, profile: LanguageProfile | None = None) -> str:
    result = translate_source(source, profile)
    assert not any(item.severity == "error" for item in result.diagnostics), result.diagnostics
    found = {item.language: item.code for item in result.translations}
    assert set(found) == {language for language, _, _ in TARGETS}
    return found["python"]


def _run_python(code: str, stdin: str = "") -> str:
    completed = subprocess.run(
        [sys.executable, "-c", code],
        input=stdin,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, f"{completed.stderr}\n{code}"
    return completed.stdout


def _same(name: str, stdin: str = "", inputs: list[str] | None = None) -> None:
    source = (FIXTURES / name).read_text(encoding="utf-8")
    expected = execute_source(source, inputs)
    assert expected.status == "completed", expected.diagnostics
    assert _run_python(_python(source), stdin) == expected.output


def test_comments_are_kept_apart_from_tokens() -> None:
    result = lex("// nota\nAlgoritmo /* bloque */ X\n")
    assert [token.lexeme for token in result.tokens if token.kind.name != "EOF"] == [
        "Algoritmo",
        "X",
    ]
    assert result.comments[0].kind == "line"
    assert result.comments[0].text == " nota"
    assert result.comments[1].kind == "block"
    assert "bloque" in result.comments[1].text


def test_hola_arreglo_factorial_y_referencia_coinciden() -> None:
    _same("hola.traza")
    _same("arreglo.traza")
    _same("matriz.traza")
    _same("factorial.traza", "5\n", ["5"])
    _same("mayor.traza", "3\n1\n", ["3", "1"])
    _same("procedimiento.traza")
    _same("doblar.traza", "4\n", ["4"])
    _same("recursivo.traza", "5\n", ["5"])


def test_division_hacia_cero_y_base_cero() -> None:
    source = """
Algoritmo Signo
    Definir n Como Entero;
    n <- -7 DIV 2;
    Escribir n;
    Escribir -7 MOD 2;
FinAlgoritmo
"""
    assert _run_python(_python(source)) == "-3\n-1\n"
    base = LanguageProfile(name="strict", index_base=0)
    zeros = """
Algoritmo Ceros
    Definir numeros, i, suma Como Entero;
    Dimension numeros[3] Como Entero;
    suma <- 0;
    Para i <- 0 Hasta 2 Hacer
        numeros[i] <- i + 1;
        suma <- suma + numeros[i];
    FinPara
    Escribir suma;
FinAlgoritmo
"""
    code = _python(zeros, base)
    assert "(i - 1)" not in code
    assert _run_python(code) == "6\n"


def test_comentarios_y_referencias_en_los_demas_lenguajes() -> None:
    source = """
// saludo
Algoritmo Notas
    Escribir "Hola"; // junto
    /* bloque */
FinAlgoritmo
"""
    result = translate_source(source)
    python = next(item.code for item in result.translations if item.language == "python")
    java = next(item.code for item in result.translations if item.language == "java")
    assert "# saludo" in python
    assert "# junto" in python or "#  junto" in python
    assert "bloque" in python
    assert "// saludo" in java
    procedure = (FIXTURES / "procedimiento.traza").read_text(encoding="utf-8")
    translated = translate_source(procedure)
    cpp = next(item.code for item in translated.translations if item.language == "cpp")
    csharp = next(item.code for item in translated.translations if item.language == "csharp")
    java = next(item.code for item in translated.translations if item.language == "java")
    assert "int&" in cpp
    assert "ref int" in csharp
    assert "_TrazaCajaInt" in java


def test_un_error_no_genera_codigo() -> None:
    result = translate_source("Algoritmo Roto\nFinAlgoritmo\nSi 1 = 1 Entonces\n")
    assert any(item.severity == "error" for item in result.diagnostics)
    assert result.translations == ()


def test_biblioteca_arreglos_de_texto_y_paso_explicito() -> None:
    source = """
SubProceso Tocar(datos Por Valor)
    Definir datos Como Entero;
    Dimension datos[1] Como Entero;
    datos[1] <- 9;
FinSubProceso
Algoritmo Amplio
    Definir print, i, salto, k, azar Como Entero;
    Definir medida, mitad Como Real;
    Definir texto Como Cadena;
    Definir letra Como Caracter;
    Definir activo Como Logico;
    Dimension numeros[1] Como Entero;
    Dimension nombres[2, 2] Como Cadena;
    Leer letra;
    Leer texto;
    Leer medida;
    Leer activo;
    numeros[1] <- 1;
    Tocar(numeros);
    Escribir numeros[1];
    mitad <- 1 / 2 + Sen(0) + Ln(1);
    Escribir mitad;
    Escribir medida;
    print <- 3;
    Escribir print;
    salto <- 2;
    k <- 0;
    Para i <- 1 Hasta 4 Con Paso salto Hacer
        k <- k + i;
    FinPara
    Mientras k < 8 Hacer
        k <- k + 1;
    FinMientras
    Escribir k;
    Si texto < "zzz" Entonces
        Escribir Mayusculas(texto);
    Sino
        Escribir Minusculas(texto);
    FinSi
    nombres[1, 1] <- "ab";
    Escribir Concatenar(nombres[1, 1], ConvertirATexto(2));
    Escribir Redon(Cos(0) + Exp(0));
    Escribir Trunc(1.9);
    Escribir Potencia(2, 3);
    Escribir Raiz(4);
    azar <- Aleatorio(1, 1);
    Escribir azar;
    Escribir ConvertirANumero("18");
    Escribir letra;
    Escribir activo;
    Esperar 0 Segundos;
    Escribir "listo";
FinAlgoritmo
"""
    stdin = "A\nhola\n2.5\nVerdadero\n"
    expected = execute_source(source, ["A", "hola", "2.5", "Verdadero"])
    assert expected.status == "completed", expected.diagnostics
    code = _python(source)
    assert "print_" in code
    assert _run_python(code, stdin) == expected.output
    translated = translate_source(source)
    java = next(item.code for item in translated.translations if item.language == "java")
    cpp = next(item.code for item in translated.translations if item.language == "cpp")
    assert "_traza_arreglo_cadena_2" in java
    assert "std::pow" in cpp or "Objects.equals" in java or "compareTo" in java


def test_la_cocina_genera_los_seis_lenguajes() -> None:
    result = translate_source(SINK)
    assert not any(item.severity == "error" for item in result.diagnostics), result.diagnostics
    assert len(result.translations) == 6
    python = next(item.code for item in result.translations if item.language == "python")
    assert "presentación" in python
    assert _run_python(python, "2\n").endswith("fin")
