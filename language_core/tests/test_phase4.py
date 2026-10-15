"""Paso a paso, llamadas y puntos de interrupción sobre el mismo intérprete."""

import pytest

from language_core.debugger import DebugRejected, open_debug

STEPS = """Algoritmo Demo
    Definir n Como Entero;
    n <- 1;
    n <- 2;
    Escribir n;
FinAlgoritmo
"""

CALL = """SubProceso Saludar()
    Escribir "hola";
FinSubProceso
Algoritmo Demo
    Saludar();
    Escribir "fin";
FinAlgoritmo
"""

READ = """Algoritmo Lee
    Definir n Como Entero;
    Leer n;
    Escribir n;
FinAlgoritmo
"""

BRANCH = """Algoritmo Demo
    Si 1 = 1 Entonces
        Escribir "si";
    FinSi
FinAlgoritmo
"""


def test_step_borra_la_pantalla_antes_de_seguir() -> None:
    session = open_debug("""
Algoritmo P
    Escribir "Hola";
    Borrar Pantalla;
    Escribir "Listo";
FinAlgoritmo
""")
    session.command("step")
    assert session.snapshot()["output"] == "Hola\n"
    session.command("step")
    assert session.snapshot()["output"] == ""
    session.command("continue")
    assert session.status == "completed"
    assert session.snapshot()["output"] == "Listo\n"


def test_step_avanza_y_termina() -> None:
    session = open_debug(STEPS)
    assert session.status == "paused"
    assert session.line == 2
    session.command("step")
    assert session.line == 3
    session.command("step")
    assert session.variables()["n"] == "1"
    session.command("step")
    assert session.variables()["n"] == "2"
    session.command("step")
    assert session.status == "completed"
    assert session.snapshot()["output"] == "2\n"


def test_entrar_y_salir_de_un_procedimiento() -> None:
    session = open_debug(CALL)
    assert session.line == 5
    session.command("step_in")
    assert session.line == 2
    assert [frame["name"] for frame in session.stack] == ["Demo", "Saludar"]
    session.command("step_out")
    assert session.line == 6
    assert session.snapshot()["output"] == "hola\n"
    session.command("step")
    assert session.status == "completed"
    assert session.snapshot()["output"] == "hola\nfin\n"


def test_un_paso_no_entra_en_la_llamada() -> None:
    session = open_debug(CALL)
    session.command("step")
    assert session.line == 6
    assert session.snapshot()["output"] == "hola\n"
    assert [frame["name"] for frame in session.stack] == ["Demo"]


def test_continuar_se_detiene_en_el_punto_de_interrupcion() -> None:
    session = open_debug(STEPS, breakpoints={4})
    session.command("continue")
    assert session.status == "paused"
    assert session.line == 4
    assert session.variables()["n"] == "1"
    session.command("continue")
    assert session.status == "completed"
    assert session.snapshot()["output"] == "2\n"


def test_punto_en_linea_vacia_avisa_y_no_detiene() -> None:
    session = open_debug(STEPS, breakpoints={1})
    assert any(item.code == "W0504" for item in session.diagnostics)
    session.command("continue")
    assert session.status == "completed"


def test_pausa_corta_en_la_siguiente_sentencia() -> None:
    session = open_debug(STEPS)
    session.pause_requested = True
    session.command("continue")
    assert session.status == "paused"
    assert session.line == 3


def test_detener_no_ejecuta_la_sentencia_actual() -> None:
    session = open_debug(STEPS)
    session.command("stop")
    assert session.status == "cancelled"
    assert session.variables() == {}
    with pytest.raises(DebugRejected):
        session.command("step")


def test_leer_dentro_de_la_depuracion() -> None:
    session = open_debug(READ)
    session.command("continue")
    assert session.status == "waiting_input"
    assert session.pending_input == {"name": "n", "type": "entero"}
    session.provide_input("no")
    assert session.status == "waiting_input"
    assert session.inputs == []
    session.provide_input("8")
    assert session.status == "completed"
    assert session.snapshot()["output"] == "8\n8\n"
    assert session.inputs == ["8"]


def test_la_condicion_queda_en_la_pausa_siguiente() -> None:
    session = open_debug(BRANCH)
    session.command("step")
    assert session.line == 3
    assert session.snapshot()["last_condition"] == "Verdadero"


def test_error_de_ejecucion_detiene_la_sesion() -> None:
    source = """Algoritmo Falla
    Definir n Como Real;
    n <- 1 / 0;
    Escribir n;
FinAlgoritmo
"""
    session = open_debug(source)
    session.command("step")
    session.command("step")
    assert session.status == "error"
    assert session.diagnostics[-1].code == "E0402"


def test_inspeccion_de_arreglo() -> None:
    source = """Algoritmo Datos
    Definir datos Como Entero;
    Dimension datos[30] Como Entero;
    datos[1] <- 7;
    Escribir datos[1];
FinAlgoritmo
"""
    session = open_debug(source)
    session.command("continue")
    assert session.status == "completed"
    paused = open_debug(source, breakpoints={4})
    paused.command("continue")
    assert "celdas" in paused.variables()["datos"]
    chunk = paused.inspect("datos", 0, 2)
    assert chunk["total"] == 30
    assert chunk["values"] == ["0", "0"]
    with pytest.raises(DebugRejected):
        paused.inspect("nada", 0, 2)


def test_la_pausa_no_consume_el_tiempo_de_ejecucion() -> None:
    class Clock:
        def __init__(self) -> None:
            self.now = 0.0

        def __call__(self) -> float:
            return self.now

    clock = Clock()
    session = open_debug(STEPS, clock=clock)
    clock.now = 30
    session.command("step")
    assert session.status == "paused"
    assert session.line == 3


def test_fuente_invalido_no_abre_el_generador() -> None:
    session = open_debug("Algoritmo Roto\n")
    assert session.status == "error"
    with pytest.raises(DebugRejected):
        session.command("continue")
