"""El diagrama sigue el AST: secuencia, decisiones, ciclos y subrutinas."""

from language_core.flowchart import build
from language_core.interpreter import compile_source


def _graph(source: str):
    compiled = compile_source(source)
    assert compiled.program is not None, compiled.diagnostics
    assert not any(item.severity == "error" for item in compiled.diagnostics)
    return build(compiled.program)


def _node(graph, text: str):
    return next(node for node in graph.nodes if node.text == text)


def _labels(graph, source: str) -> set[str | None]:
    node = _node(graph, source)
    return {edge.label for edge in graph.edges if edge.source == node.id}


def test_secuencia_une_inicio_procesos_y_fin() -> None:
    graph = _graph("""
Algoritmo Demo
    Definir a Como Entero;
    a <- 1;
    Escribir a;
FinAlgoritmo
""")
    assert graph.entry == "n1"
    assert [node.kind for node in graph.nodes] == [
        "terminal",
        "process",
        "process",
        "io",
        "terminal",
    ]
    assert [node.text for node in graph.nodes] == [
        "Inicio",
        "Definir a Como Entero",
        "a <- 1",
        "Escribir a",
        "Fin",
    ]
    assert graph.nodes[3].figure == "output"
    assert graph.edges[-1].target == graph.nodes[-1].id
    payload = graph.as_dict()
    assert payload["entry"] == "n1"
    assert isinstance(payload["nodes"], list)


def test_condicional_marca_la_linea_del_si_y_une_las_ramas() -> None:
    graph = _graph("""
Algoritmo Demo
    Definir a Como Entero;
    a <- 1;
    Si a = 1 Entonces
        Escribir a;
    Sino
        Escribir 0;
    FinSi
FinAlgoritmo
""")
    decision = _node(graph, "a = 1")
    assert decision.kind == "decision"
    assert decision.figure == "decision"
    assert decision.span is not None
    assert decision.span.start_line == 5
    assert _labels(graph, "a = 1") == {"Sí", "No"}
    join = next(node for node in graph.nodes if node.kind == "join")
    targets = {
        edge.target
        for edge in graph.edges
        if edge.source in {_node(graph, "Escribir a").id, _node(graph, "Escribir 0").id}
    }
    assert join.id in targets


def test_si_sin_sino_lleva_el_no_al_join() -> None:
    graph = _graph("""
Algoritmo Demo
    Si 1 = 1 Entonces
        Escribir 1;
    FinSi
FinAlgoritmo
""")
    assert _labels(graph, "1 = 1") == {"Sí", "No"}
    no = next(edge for edge in graph.edges if edge.label == "No")
    assert next(node for node in graph.nodes if node.id == no.target).kind == "join"


def test_mientras_vuelve_al_rombo_y_el_no_sale() -> None:
    graph = _graph("""
Algoritmo Demo
    Definir n Como Entero;
    n <- 0;
    Mientras n < 3 Hacer
        n <- n + 1;
    FinMientras
FinAlgoritmo
""")
    decision = _node(graph, "n < 3")
    assert decision.figure == "loop"
    back = next(edge for edge in graph.edges if edge.target == decision.id and edge.source != "n1")
    assert back.label is None
    assert "No" in _labels(graph, "n < 3")
    assert "Sí" in _labels(graph, "n < 3")


def test_repetir_pone_el_rombo_despues_del_cuerpo() -> None:
    graph = _graph("""
Algoritmo Demo
    Definir n Como Entero;
    n <- 0;
    Repetir
        n <- n + 1;
    Hasta Que n = 3
FinAlgoritmo
""")
    decision = _node(graph, "n = 3")
    body = _node(graph, "n <- n + 1")
    assert body.id < decision.id
    back = next(edge for edge in graph.edges if edge.source == decision.id and edge.label == "No")
    assert back.target == body.id
    onward = next(edge for edge in graph.edges if edge.source == decision.id and edge.label == "Sí")
    assert next(node for node in graph.nodes if node.id == onward.target).text == "Fin"


def test_para_dibuja_inicio_continuacion_cuerpo_e_incremento() -> None:
    graph = _graph("""
Algoritmo Demo
    Definir i Como Entero;
    Para i <- 1 Hasta 3 Con Paso 1 Hacer
        Escribir i;
    FinPara
FinAlgoritmo
""")
    assert _node(graph, "i <- 1").kind == "process"
    assert _node(graph, "i <= 3").kind == "decision"
    assert _node(graph, "i <- i + 1").kind == "process"
    decision = _node(graph, "i <= 3")
    assert any(
        edge.source == _node(graph, "i <- i + 1").id and edge.target == decision.id
        for edge in graph.edges
    )
    negative = _graph("""
Algoritmo Demo
    Definir i, n Como Entero;
    n <- 1;
    Para i <- 3 Hasta 1 Con Paso -1 Hacer
        Escribir i;
    FinPara
    Para i <- 1 Hasta 3 Con Paso n Hacer
        Escribir i;
    FinPara
FinAlgoritmo
""")
    assert _node(negative, "i >= 1").kind == "decision"
    assert _node(negative, "i <- i + -1").kind == "process"
    assert any(node.text == "i hasta 3" for node in negative.nodes)


def test_segun_etiqueta_casos_y_el_caso_omiso() -> None:
    graph = _graph("""
Algoritmo Demo
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
""")
    assert _node(graph, "opcion").kind == "decision"
    assert _node(graph, "opcion").figure == "switch"
    assert _labels(graph, "opcion") == {"1", "2, 3", "De Otro Modo"}
    bare = _graph("""
Algoritmo Demo
    Segun 1 Hacer
        1:
            Escribir 1;
    FinSegun
FinAlgoritmo
""")
    assert None in _labels(bare, "1")


def test_llamada_es_subproceso_y_cada_rutina_tiene_extremos() -> None:
    graph = _graph("""
Funcion resultado <- Doblar(n)
    Definir resultado, n Como Entero;
    resultado <- n * 2;
FinFuncion
SubProceso Saludar()
    Escribir "hola";
FinSubProceso
Algoritmo Demo
    Definir numero Como Entero;
    Leer numero;
    Escribir Doblar(numero);
    Saludar();
FinAlgoritmo
""")
    call = _node(graph, "Saludar()")
    assert call.kind == "subprocess"
    write = _node(graph, "Escribir Doblar(numero)")
    assert write.kind == "io"
    assert any(node.text == "Inicio Doblar" for node in graph.nodes)
    assert any(node.text == "Fin Saludar" for node in graph.nodes)
    assert graph.nodes[0].text == "Inicio"


def test_arreglo_dimension_y_asignacion_indexada() -> None:
    graph = _graph("""
Algoritmo Demo
    Definir datos, i Como Entero;
    Dimension datos[5] Como Entero;
    datos[1] <- 4;
    Leer datos[i];
    Escribir datos[i];
FinAlgoritmo
""")
    assert _node(graph, "Dimension datos[5] Como Entero").kind == "process"
    assert _node(graph, "datos[1] <- 4").kind == "process"
    assert _node(graph, "Leer datos[i]").kind == "io"


def test_expresiones_respetan_la_precedencia() -> None:
    graph = _graph("""
Algoritmo Demo
    Definir n Como Entero;
    Definir a Como Logico;
    n <- -2 ^ 2;
    n <- (-2) ^ 2;
    n <- 7 DIV 2;
    n <- 7 MOD 2;
    a <- NO Verdadero;
    Si NO a Y Verdadero Entonces
        Escribir 1;
    FinSi
    Si NO (a Y Verdadero) Entonces
        Escribir 0;
    FinSi
FinAlgoritmo
""")
    texts = {node.text for node in graph.nodes}
    assert "n <- -2 ^ 2" in texts
    assert "n <- (-2) ^ 2" in texts
    assert "n <- 7 DIV 2" in texts
    assert "n <- 7 MOD 2" in texts
    assert "a <- NO Verdadero" in texts
    assert "NO a Y Verdadero" in texts
    assert "NO (a Y Verdadero)" in texts


def test_algoritmo_vacio_solo_une_los_extremos() -> None:
    graph = _graph("Algoritmo Vacio\nFinAlgoritmo\n")
    assert [node.text for node in graph.nodes] == ["Inicio", "Fin"]
    assert len(graph.edges) == 1


def test_ciclos_vacios_siguen_teniendo_retorno() -> None:
    graph = _graph("""
Algoritmo Demo
    Definir i Como Entero;
    Mientras 1 = 0 Hacer
    FinMientras
    Repetir
    Hasta Que 1 = 1
    Para i <- 1 Hasta 1 Hacer
    FinPara
FinAlgoritmo
""")
    while_node = _node(graph, "1 = 0")
    assert any(
        edge.source == while_node.id and edge.target == while_node.id for edge in graph.edges
    )
    repeat = _node(graph, "1 = 1")
    assert any(
        edge.source == repeat.id and edge.target == repeat.id and edge.label == "No"
        for edge in graph.edges
    )
    assert any(node.text == "i <- i ± 1" for node in graph.nodes)
