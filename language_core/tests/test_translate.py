"""La traducción conserva el resultado del intérprete y los comentarios."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
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


def _written(output: str, inputs: list[str] | None) -> str:
    """Quita las líneas que el intérprete repite al aceptar un Leer."""
    if not inputs:
        return output
    pending = [f"{item}\n" for item in inputs]
    kept: list[str] = []
    for line in output.splitlines(keepends=True):
        if pending and line == pending[0]:
            pending.pop(0)
            continue
        kept.append(line)
    return "".join(kept)


def _same(name: str, stdin: str = "", inputs: list[str] | None = None) -> None:
    source = (FIXTURES / name).read_text(encoding="utf-8")
    expected = execute_source(source, inputs)
    assert expected.status == "completed", expected.diagnostics
    assert _run_python(_python(source), stdin) == _written(expected.output, inputs)


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
    c_code = next(item.code for item in translated.translations if item.language == "c")
    assert "int *n" in c_code
    assert "Incrementar(&edad)" in c_code


def test_segun_usa_switch_o_if() -> None:
    source = """
Algoritmo Seleccion
    Definir n Como Entero;
    n <- 2;
    Segun n Hacer
        1: Escribir "uno";
        2, 3: Escribir "varios";
    De Otro Modo:
        Escribir "otro";
    FinSegun
FinAlgoritmo
"""
    codes = {item.language: item.code for item in translate_source(source).translations}
    assert "match " in codes["python"]
    assert "case 2 | 3:" in codes["python"]
    assert _run_python(codes["python"]) == "varios\n"
    for language in ("javascript", "typescript", "java", "c", "cpp", "csharp"):
        assert "switch (" in codes[language]
        assert "case 2:" in codes[language]
        assert "case 3:" in codes[language]
        assert "break;" in codes[language]
        assert "default:" in codes[language]
    assert _run_c(codes["c"]) == "varios\n"
    texto = """
Algoritmo Texto
    Definir s Como Cadena;
    s <- "ab";
    Segun s Hacer
        "ab": Escribir "si";
    De Otro Modo:
        Escribir "no";
    FinSegun
FinAlgoritmo
"""
    textual = {item.language: item.code for item in translate_source(texto).translations}
    assert "switch (" in textual["java"]
    assert 'case "ab":' in textual["java"]
    assert "switch (" not in textual["c"]
    assert "strcmp" in textual["c"]
    real = """
Algoritmo Medida
    Definir x Como Real;
    x <- 1.5;
    Segun x Hacer
        1.5: Escribir "si";
    FinSegun
FinAlgoritmo
"""
    numbers = {item.language: item.code for item in translate_source(real).translations}
    assert "switch (" in numbers["javascript"]
    assert "switch (" not in numbers["java"]
    assert "if (" in numbers["java"]
    assert _run_python(numbers["python"]) == "si\n"


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
    assert "float(input())" in code
    assert "_traza_leer_" not in code
    assert "_traza_texto_real" not in code
    output = _run_python(code, stdin)
    assert "HOLA" in output
    assert "ab2" in output
    assert output.endswith("listo\n")
    assert "for i in range(1, 4 + (1 if salto > 0 else -1), salto):" in code
    assert "while k < 8:" in code
    assert "numeros = [0] * (1)" in code
    assert 'nombres = [[""] * (2) for _ in range(2)]' in code
    assert "_traza_arreglo" not in code
    assert "_traza_desde_" not in code
    translated = translate_source(source)
    java = next(item.code for item in translated.translations if item.language == "java")
    cpp = next(item.code for item in translated.translations if item.language == "cpp")
    assert "new String[2][2]" in java
    assert "for (i = 1; (salto > 0 ? i <= 4 : i >= 4); i = i + salto)" in java
    assert "_traza_arreglo" not in java
    assert "std::vector<std::vector<std::string>> nombres" in cpp
    assert "_traza_leer_" not in java
    assert "_traza_texto_real" not in java
    assert "Double.parseDouble" in java
    assert "System.out.println" in java
    assert "std::cin >>" in cpp


def test_la_cocina_genera_los_lenguajes() -> None:
    result = translate_source(SINK)
    assert not any(item.severity == "error" for item in result.diagnostics), result.diagnostics
    assert len(result.translations) == len(TARGETS)
    python = next(item.code for item in result.translations if item.language == "python")
    assert "presentación" in python
    assert _run_python(python, "2\n").endswith("fin")


def _run_c(code: str, stdin: str = "") -> str:
    compiler = shutil.which("cc")
    assert compiler is not None
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "programa.c"
        binary = Path(folder) / "programa"
        path.write_text(code, encoding="utf-8")
        compiled = subprocess.run(
            [
                compiler,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Wno-unused-variable",
                "-o",
                str(binary),
                str(path),
                "-lm",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert compiled.returncode == 0, f"{compiled.stderr}\n{code}"
        ran = subprocess.run(
            [str(binary)],
            input=stdin,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        assert ran.returncode == 0, ran.stderr
        return ran.stdout


def _python_and_c(source: str) -> tuple[str, str]:
    result = translate_source(source)
    assert not any(item.severity == "error" for item in result.diagnostics), result.diagnostics
    found = {item.language: item.code for item in result.translations}
    return found["python"], found["c"]


def test_c_compila_y_coincide_con_python() -> None:
    samples = [
        ((FIXTURES / "hola.traza").read_text(encoding="utf-8"), ""),
        ((FIXTURES / "arreglo.traza").read_text(encoding="utf-8"), ""),
        ((FIXTURES / "matriz.traza").read_text(encoding="utf-8"), ""),
        ((FIXTURES / "factorial.traza").read_text(encoding="utf-8"), "5\n"),
        ((FIXTURES / "procedimiento.traza").read_text(encoding="utf-8"), ""),
        ((FIXTURES / "doblar.traza").read_text(encoding="utf-8"), "4\n"),
        (
            """
Algoritmo Ciclos
    Definir i, a, b Como Entero;
    Para i <- 3 Hasta 1 Hacer
        Escribir i;
    FinPara
    Para i <- 4 Hasta 1 Con Paso -2 Hacer
        Escribir i;
    FinPara
    a <- 2;
    b <- 4;
    Para i <- a Hasta b Hacer
        Escribir i;
    FinPara
FinAlgoritmo
""",
            "",
        ),
        (SINK, "2\n"),
        (
            """
SubProceso Tocar(datos Por Valor)
    Definir datos Como Entero;
    Dimension datos[1] Como Entero;
    datos[1] <- 9;
FinSubProceso
Algoritmo Amplio
    Definir letra Como Caracter;
    Definir texto Como Cadena;
    Definir medida Como Real;
    Definir activo Como Logico;
    Definir azar Como Entero;
    Dimension numeros[1] Como Entero;
    Dimension nombres[2, 2] Como Cadena;
    Leer letra;
    Leer texto;
    Leer medida;
    Leer activo;
    numeros[1] <- 1;
    Tocar(numeros);
    Escribir numeros[1];
    nombres[1, 1] <- "ab";
    Escribir Concatenar(nombres[1, 1], ConvertirATexto(2));
    Si texto < "zzz" Entonces
        Escribir Mayusculas(texto);
    FinSi
    Escribir Redon(Cos(0) + Exp(0));
    Escribir Raiz(4);
    azar <- Aleatorio(1, 1);
    Escribir azar;
    Escribir medida;
    Escribir letra;
    Escribir activo;
    Esperar 0 Segundos;
    Escribir "listo";
FinAlgoritmo
""",
            "A\nhola\n2.5\nVerdadero\n",
        ),
    ]
    amplio_source, amplio_stdin = samples.pop()
    for source, stdin in samples:
        python, c_code = _python_and_c(source)
        output = _run_python(python, stdin)
        assert _run_c(c_code, stdin) == output
        assert "_TrazaVec" not in c_code
        assert "_traza_desde_" not in c_code
        assert "_traza_nuevo_" not in c_code
        if "Algoritmo Ciclos" in source:
            assert output == "3\n2\n1\n4\n2\n2\n3\n4\n"
            assert "for (i = 3; i >= 1; i--)" in c_code
    python, c_code = _python_and_c(amplio_source)
    assert "scanf" in c_code
    assert "_traza_leer_" not in c_code
    assert "int numeros[1] = {0};" in c_code
    assert "char *nombres[2][2] = {0};" in c_code
    assert "_TrazaVec" not in c_code
    c_output = _run_c(c_code, amplio_stdin)
    python_output = _run_python(python, amplio_stdin)
    assert "HOLA" in c_output and "HOLA" in python_output
    assert c_output.endswith("listo\n") and python_output.endswith("listo\n")
