"""La práctica de concurso trae 50 programas y el CSV crea retos de los cuatro tipos."""

import pytest
from rest_framework.test import APIClient

from apps.learning.contest_data import (
    CONTEST_BANK_NAME,
    CONTEST_ROUTE_NAME,
    build_contest,
)
from apps.learning.csv_import import template_csv
from apps.learning.models import Challenge, ChallengeAttempt, PathEntry, WorkspaceSnapshot
from apps.tests.helpers import register
from language_core.block_import import workspace_from_source

pytestmark = pytest.mark.django_db


def test_el_banco_de_concurso_tiene_cincuenta_programas_con_casos():
    bank = build_contest()
    challenges = [item for unit in bank["units"] for item in unit["challenges"]]
    assert len(challenges) == 50
    assert {item["activity_type"] for item in challenges} == {"build"}
    first = challenges[0]
    assert first["cases"][0]["expected_output"].endswith("8\n")
    assert first["cases"][0]["inputs"] == ["3", "5"]
    for item in challenges:
        assert len(item["cases"]) == 3
        assert [case["kind"] for case in item["cases"]] == ["normal", "normal", "boundary"]
        assert item["restrictions"]["tools"] == ["codigo", "diagrama", "bloques"]
        assert "source" not in item["restrictions"]
        assert any("Esta es la solución explicada" in hint["body"] for hint in item["hints"])


def test_la_ruta_de_concurso_queda_publicada_en_orden():
    stored = Challenge.objects.filter(unit__path__name=CONTEST_BANK_NAME, is_published=True)
    assert stored.count() == 50
    bank = stored.first().unit.path
    assert bank.is_bank is True
    assert bank.owner_id is None
    route_ids = list(
        PathEntry.objects.filter(path__name=CONTEST_ROUTE_NAME)
        .order_by("position")
        .values_list("challenge_id", flat=True)
    )
    ordered = list(stored.order_by("unit__position", "position").values_list("id", flat=True))
    assert route_ids == ordered
    route = PathEntry.objects.filter(path__name=CONTEST_ROUTE_NAME).first().path
    assert route.is_bank is False
    assert route.is_published is True

    student = APIClient()
    register(student, email="concurso-alumno@ejemplo.test", display_name="Alumno Concurso")
    listed = student.get("/api/v1/learning/paths/").json()["results"]
    contest = next(item for item in listed if item["name"] == CONTEST_ROUTE_NAME)
    assert len(contest["challenges"]) == 50
    assert contest["challenges"][0]["state"] == "available"
    assert contest["challenges"][1]["state"] == "locked"
    assert contest["challenges"][0]["activity_type"] == "build"


def test_el_docente_ve_el_banco_de_concurso_aparte_del_catalogo():
    teacher = APIClient()
    register(
        teacher, email="concurso-profe@ejemplo.test", display_name="Profe Concurso", role="teacher"
    )
    body = teacher.get("/api/v1/learning/bank/").json()
    catalog = [item for unit in body["units"] for item in unit["challenges"]]
    contest = [item for unit in body["contest"]["units"] for item in unit["challenges"]]
    assert len(catalog) == 200
    assert body["contest"]["name"] == CONTEST_BANK_NAME
    assert len(contest) == 50
    assert contest[0]["cases"][0]["name"] == "ejemplo"
    assert contest[0]["owned"] is False


def test_un_alumno_no_carga_csv(client):
    register(client, email="csv-alumno@ejemplo.test")
    response = client.post("/api/v1/learning/challenges/csv/", {"csv": "tipo\n"}, format="json")
    assert response.status_code == 403


def test_cada_plantilla_se_importa():
    teacher = APIClient()
    register(teacher, email="csv-profe@ejemplo.test", display_name="Profe CSV", role="teacher")
    spec = teacher.get("/api/v1/learning/challenges/csv/").json()
    assert [item["tipo"] for item in spec["types"]] == [
        "clasificar",
        "ordenar",
        "construir",
        "predecir",
    ]
    for kind in ("clasificar", "ordenar", "construir", "predecir"):
        downloaded = teacher.get(f"/api/v1/learning/challenges/csv/?tipo={kind}").json()
        assert downloaded["csv"] == template_csv(kind)
        created = teacher.post(
            "/api/v1/learning/challenges/csv/",
            {"csv": downloaded["csv"]},
            format="json",
        )
        assert created.status_code == 201, created.content
        assert created.json()["created"] == 1
    bank = teacher.get("/api/v1/learning/bank/").json()
    titles = {
        item["title"] for unit in bank["units"] for item in unit["challenges"] if item["owned"]
    }
    assert titles == {
        "Señales del dato",
        "Pasos del saludo",
        "El doble leído",
        "Después de sumar uno",
    }
    built = next(
        item
        for unit in bank["units"]
        for item in unit["challenges"]
        if item["title"] == "El doble leído"
    )
    assert len(built["cases"]) == 3
    assert built["cases"][0]["expected_output"] == "6\n12\n"


def test_un_csv_con_punto_y_coma_y_un_error_no_dejan_retos_a_medias():
    teacher = APIClient()
    register(teacher, email="csv-mixto@ejemplo.test", display_name="Profe Mixto", role="teacher")
    semicolon = (
        "tipo;titulo;enunciado;concepto;dificultad;puntos;minutos;instrucciones;pista1\n"
        "ordenar;Orden local;Ordena los pasos.;assignment;1;10;;"
        "Definir n como entero|Leer n|Escribir n;Empieza por definir.\n"
    )
    assert (
        teacher.post(
            "/api/v1/learning/challenges/csv/",
            {"csv": semicolon},
            format="json",
        ).status_code
        == 201
    )
    broken = (
        "tipo,titulo,enunciado,concepto,pregunta,respuestas,caso1_salida,caso3_salida\n"
        "construir,Uno bueno,Lee y escribe.,io,¿Cuál?,1,1,\n"
        "construir,Uno malo,Lee y escribe.,inventado,¿Cuál?,1,,2\n"
    )
    failed = teacher.post("/api/v1/learning/challenges/csv/", {"csv": broken}, format="json")
    assert failed.status_code == 400
    assert "Uno bueno" not in failed.json()["error"]["message"]
    assert "concepto" in failed.json()["error"]["message"].casefold()
    duplicate = (
        "tipo,titulo,enunciado,concepto,instrucciones\n"
        "ordenar,Repetido,Ordena.,assignment,Definir n como entero|Leer n\n"
        "ordenar,Repetido,Otra vez.,assignment,Definir n como entero|Escribir n\n"
    )
    again = teacher.post("/api/v1/learning/challenges/csv/", {"csv": duplicate}, format="json")
    assert again.status_code == 400
    assert "Fila 3" in again.json()["error"]["message"]
    bank = teacher.get("/api/v1/learning/bank/").json()
    titles = [
        item["title"] for unit in bank["units"] for item in unit["challenges"] if item["owned"]
    ]
    assert titles == ["Orden local"]


def test_un_caso_acepta_las_lecturas_de_un_juego_largo():
    teacher = APIClient()
    register(teacher, email="csv-palillos@ejemplo.test", display_name="Profe Palillos", role="teacher")
    csv = r"""tipo,titulo,enunciado,concepto,dificultad,puntos,minutos,pregunta,respuestas,caso1_entradas,caso1_salida,caso2_entradas,caso2_salida,caso3_entradas,caso3_salida,caso4_entradas,caso4_salida,caso5_entradas,caso5_salida,caso6_entradas,caso6_salida,pista1,pista2,pista3,pista4,pista5
construir,Duelo de palillos,Construye en PSeInt un juego de palillos para dos jugadores humanos. No uses jugadas automáticas; arreglos ni funciones. Pierde quien retire el último palillo; incluso si retira varios y deja la pila en cero. Lee todos los datos como enteros; uno por lectura. 1. Lee el total de palillos. Debe ser al menos 5; si no cumple; escribe TOTAL INVALIDO y vuelve a leerlo. 2. Lee el máximo por turno. Debe estar entre 1 y el total inicial; si no cumple; escribe MAXIMO INVALIDO y vuelve a leerlo. 3. Lee el jugador inicial: 1 o 2. Si no cumple; escribe JUGADOR INVALIDO y vuelve a leerlo. 4. Antes de cada turno escribe TURNO seguido de un espacio y el número de jugador; después escribe RESTANTES seguido de un espacio y los palillos disponibles; en otra línea. 5. Lee el retiro. Debe ser al menos 1; no superar el máximo ni los palillos restantes. Si es inválido; escribe RETIRO INVALIDO y vuelve a leer solo el retiro; sin cambiar de jugador ni repetir el encabezado del turno. 6. Resta el retiro válido. Si quedan palillos; cambia de jugador y comienza el siguiente turno. Si quedan cero; escribe PIERDE seguido de un espacio y el jugador actual; en otra línea escribe GANA seguido de un espacio y el otro jugador. Termina sin solicitar más datos. Cuando queda uno; el jugador debe ingresar 1: también hay interacción en la última jugada. Contrato de salida para evaluación: usa exactamente los textos anteriores; sin tildes; títulos; preguntas; líneas vacías ni mensajes adicionales. Para formar cada mensaje puedes usar Escribir con el texto y la variable. Las entradas contienen únicamente enteros; no se pide validar letras o decimales. Los casos de salida siguen la convención de la plantilla: incluyen cada valor leído como eco; además de las líneas escritas por el algoritmo. No agregues instrucciones Escribir para duplicar ese eco. Las entradas de cada caso se separan con | y las líneas de salida con la secuencia literal \n. Ejemplo: total 11; máximo 3; comienza el jugador 2; retiros 3; 2; 3; 2; 1. Pierde el jugador 2 y gana el jugador 1.,while,5,100,60,¿Qué debe ocurrir cuando un retiro es inválido?,Se solicita otro retiro sin cambiar de jugador|Repetir la lectura del retiro y conservar el turno,11|3|2|3|2|3|2|1,11\n3\n2\nTURNO 2\nRESTANTES 11\n3\nTURNO 1\nRESTANTES 8\n2\nTURNO 2\nRESTANTES 6\n3\nTURNO 1\nRESTANTES 3\n2\nTURNO 2\nRESTANTES 1\n1\nPIERDE 2\nGANA 1\n,5|1|1|1|1|1|1|1,5\n1\n1\nTURNO 1\nRESTANTES 5\n1\nTURNO 2\nRESTANTES 4\n1\nTURNO 1\nRESTANTES 3\n1\nTURNO 2\nRESTANTES 2\n1\nTURNO 1\nRESTANTES 1\n1\nPIERDE 1\nGANA 2\n,5|5|2|5,5\n5\n2\nTURNO 2\nRESTANTES 5\n5\nPIERDE 2\nGANA 1\n,0|4|5|0|-2|6|2|0|3|1|0|-1|3|2|2|2|1,0\nTOTAL INVALIDO\n4\nTOTAL INVALIDO\n5\n0\nMAXIMO INVALIDO\n-2\nMAXIMO INVALIDO\n6\nMAXIMO INVALIDO\n2\n0\nJUGADOR INVALIDO\n3\nJUGADOR INVALIDO\n1\nTURNO 1\nRESTANTES 5\n0\nRETIRO INVALIDO\n-1\nRETIRO INVALIDO\n3\nRETIRO INVALIDO\n2\nTURNO 2\nRESTANTES 3\n2\nTURNO 1\nRESTANTES 1\n2\nRETIRO INVALIDO\n1\nPIERDE 1\nGANA 2\n,6|4|1|4|3|2,6\n4\n1\nTURNO 1\nRESTANTES 6\n4\nTURNO 2\nRESTANTES 2\n3\nRETIRO INVALIDO\n2\nPIERDE 2\nGANA 1\n,8|3|2|1|3|3|2|1,8\n3\n2\nTURNO 2\nRESTANTES 8\n1\nTURNO 1\nRESTANTES 7\n3\nTURNO 2\nRESTANTES 4\n3\nTURNO 1\nRESTANTES 1\n2\nRETIRO INVALIDO\n1\nPIERDE 1\nGANA 2\n,Define como Entero el total inicial y el máximo y el jugador actual y los palillos restantes y el retiro. Valida cada dato inicial antes de leer el siguiente.,Cada Escribir cierra con un salto de línea. Respeta exactamente los mensajes y los espacios. Las lecturas ya aparecen como eco en la salida esperada.,Usa Repetir para validar cada lectura. Un retiro es válido si retiro >= 1 Y retiro <= maximo Y retiro <= restantes. Una lectura inválida no modifica la pila ni el jugador.,Mantén la partida con Mientras restantes > 0. Después de un retiro válido resta los palillos. Si quedan cero pierde el jugador actual. Si quedan palillos cambia el jugador mediante jugador <- 3 - jugador.,Esta es la solución explicada: en el caso 1 quedan sucesivamente 8 y 6 y 3 y 1 y 0 palillos. El jugador 2 retira el último y gana el jugador 1. Los otros casos verifican los límites y las lecturas inválidas y la derrota al vaciar la pila.
"""
    created = teacher.post("/api/v1/learning/challenges/csv/", {"csv": csv}, format="json")
    assert created.status_code == 201, created.content
    bank = teacher.get("/api/v1/learning/bank/").json()
    stored = _owned(bank, "Duelo de palillos")
    assert len(stored["cases"]) == 6
    assert len(stored["cases"][3]["inputs"]) == 17
    assert stored["cases"][0]["expected_output"].startswith("11\n3\n2\nTURNO 2\n")


def test_el_formato_rechaza_un_tipo_desconocido():
    teacher = APIClient()
    register(teacher, email="csv-tipo@ejemplo.test", display_name="Profe Tipo", role="teacher")
    response = teacher.get("/api/v1/learning/challenges/csv/?tipo=dibujo")
    assert response.status_code == 400


def _owned(bank: dict, title: str) -> dict:
    return next(
        item
        for unit in bank["units"]
        for item in unit["challenges"]
        if item["owned"] and item["title"] == title
    )


def test_un_docente_descarga_los_retos_de_un_tipo_y_otro_los_carga():
    author = APIClient()
    register(author, email="csv-exporta@ejemplo.test", display_name="Profe Exporta", role="teacher")
    student = APIClient()
    register(student, email="csv-exporta-alumno@ejemplo.test")
    assert (
        student.get("/api/v1/learning/challenges/csv/?tipo=clasificar&contenido=retos").status_code
        == 403
    )

    for kind in ("clasificar", "ordenar", "construir", "predecir"):
        created = author.post(
            "/api/v1/learning/challenges/csv/",
            {"csv": template_csv(kind)},
            format="json",
        )
        assert created.status_code == 201, created.content

    colleague = APIClient()
    register(
        colleague, email="csv-recibe@ejemplo.test", display_name="Profe Recibe", role="teacher"
    )
    expected = {
        "clasificar": "Señales del dato",
        "ordenar": "Pasos del saludo",
        "construir": "El doble leído",
        "predecir": "Después de sumar uno",
    }
    bodies = {}
    for kind, title in expected.items():
        exported = author.get(f"/api/v1/learning/challenges/csv/?tipo={kind}&contenido=retos")
        assert exported.status_code == 200, exported.content
        body = exported.json()
        assert body["count"] >= 1
        assert title in body["csv"]
        assert body["csv"].splitlines()[0].startswith("tipo,titulo,enunciado,concepto")
        csv_text = body["csv"]
        expected_count = body["count"]
        if kind == "predecir":
            import csv as csvmod
            import io

            rows = list(csvmod.DictReader(io.StringIO(csv_text)))
            own = next(row for row in rows if row["pregunta"] == "¿Qué número se escribe?")
            buffer = io.StringIO()
            writer = csvmod.DictWriter(buffer, fieldnames=rows[0].keys(), lineterminator="\n")
            writer.writeheader()
            writer.writerow(own)
            csv_text = buffer.getvalue()
            expected_count = 1
        loaded = colleague.post(
            "/api/v1/learning/challenges/csv/", {"csv": csv_text}, format="json"
        )
        assert loaded.status_code == 201, loaded.content
        assert loaded.json()["created"] == expected_count
        bodies[kind] = body
    body = bodies["clasificar"]
    assert body["filename"] == "retos-clasificar.csv"

    origin = author.get("/api/v1/learning/bank/").json()
    copy = colleague.get("/api/v1/learning/bank/").json()
    source = _owned(origin, "Señales del dato")
    shared = _owned(copy, "Señales del dato")
    assert shared["categories"] == source["categories"]
    assert shared["items"] == source["items"]
    assert shared["hints"] == source["hints"]
    assert shared["concept"] == source["concept"]
    assert shared["difficulty"] == source["difficulty"]
    assert shared["points"] == source["points"]
    built = _owned(origin, "El doble leído")
    built_copy = _owned(copy, "El doble leído")
    assert built_copy["cases"] == built["cases"]
    assert built_copy["accepted"] == built["accepted"]
    predicted = _owned(origin, "Después de sumar uno")
    predicted_copy = _owned(copy, "Después de sumar uno")
    assert predicted_copy["source"] == predicted["source"]
    assert predicted_copy["accepted"] == predicted["accepted"]
    ordered = _owned(origin, "Pasos del saludo")
    ordered_copy = _owned(copy, "Pasos del saludo")
    assert [item["text"] for item in ordered_copy["items"]] == [
        item["text"] for item in ordered["items"]
    ]

    contest = author.get(
        "/api/v1/learning/challenges/csv/?tipo=clasificar&contenido=retos&banco=concurso"
    )
    assert contest.status_code == 400
    programs = author.get(
        "/api/v1/learning/challenges/csv/?tipo=construir&contenido=retos&banco=concurso"
    )
    assert programs.status_code == 200, programs.content
    assert programs.json()["count"] == 50
    assert programs.json()["filename"] == "retos-construir-concurso.csv"


def test_el_primer_caso_no_alcanza_si_faltan_los_demas(client):
    register(client, email="casos-alumno@ejemplo.test", display_name="Alumno Casos")
    listed = client.get("/api/v1/learning/paths/").json()["results"]
    route = next(item for item in listed if item["name"] == CONTEST_ROUTE_NAME)
    challenge = route["challenges"][0]
    assert challenge["title"] == "01 · Suma de dos enteros"
    opened = client.post(
        f"/api/v1/learning/challenges/{challenge['id']}/attempts/",
        {"path_id": route["id"]},
        format="json",
    )
    assert opened.status_code == 200, opened.content
    attempt_id = opened.json()["attempt"]["id"]
    understood = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/stage/",
        {"stage": "comprender", "answer": {"ack": True}},
        format="json",
    )
    assert understood.status_code == 200, understood.content
    reasoned = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/stage/",
        {"stage": "razonar", "answer": {"text": "+"}},
        format="json",
    )
    assert reasoned.status_code == 200, reasoned.content
    source = "\n".join(
        [
            "Algoritmo Suma",
            "    Definir a, b Como Entero;",
            "    Leer a;",
            "    Leer b;",
            "    Escribir 8;",
            "FinAlgoritmo",
            "",
        ]
    )
    imported = workspace_from_source(source)
    assert imported.workspace is not None
    checked = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/check/",
        {"workspace": imported.workspace},
        format="json",
    )
    assert checked.status_code == 200, checked.content
    body = checked.json()
    assert body["passed"] is False
    assert [item["passed"] for item in body["cases"]] == [True, False, False]
    assert body["attempt"]["next_stage"] == "comprobar"
    closed = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/close/",
        {"reflection": "Ya entiendo cómo funciona este reto."},
        format="json",
    )
    assert closed.status_code == 409
    snap = (
        WorkspaceSnapshot.objects.filter(attempt_id=attempt_id, schema_version=2)
        .order_by("-created_at")
        .first()
    )
    stored = dict(snap.blockly_json)
    answer = dict(stored["answer"])
    answer["passed"] = True
    stored["answer"] = answer
    snap.blockly_json = stored
    snap.save(update_fields=["blockly_json"])
    attempt = ChallengeAttempt.objects.get(pk=attempt_id)
    WorkspaceSnapshot.objects.create(
        attempt=attempt,
        schema_version=2,
        blockly_json={
            "stage": "lenguaje",
            "mark": 1,
            "answer": {
                "language": "python",
                "source": "print(1)\n",
                "outputs": [
                    case.expected_output
                    for case in attempt.challenge.test_cases.order_by("position")
                ],
                "passed": True,
                "percent": 100,
            },
        },
    )
    forced = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/close/",
        {"reflection": "Ya entiendo cómo funciona este reto."},
        format="json",
    )
    assert forced.status_code == 409, forced.content
    assert "todos los casos" in forced.json()["error"]["message"]


def test_al_terminar_queda_la_forma_en_que_respondio(client):
    register(client, email="forma-alumno@ejemplo.test", display_name="Alumno Forma")
    listed = client.get("/api/v1/learning/paths/").json()["results"]
    route = next(item for item in listed if item["name"] == CONTEST_ROUTE_NAME)
    challenge = route["challenges"][0]
    opened = client.post(
        f"/api/v1/learning/challenges/{challenge['id']}/attempts/",
        {"path_id": route["id"]},
        format="json",
    )
    assert opened.status_code == 200, opened.content
    attempt_id = opened.json()["attempt"]["id"]
    assert "solution" not in opened.json()["attempt"]
    for stage, answer in (
        ("comprender", {"ack": True}),
        ("razonar", {"text": "+"}),
    ):
        saved = client.post(
            f"/api/v1/learning/attempts/{attempt_id}/stage/",
            {"stage": stage, "answer": answer},
            format="json",
        )
        assert saved.status_code == 200, saved.content
    source = "\n".join(
        [
            "Algoritmo Suma",
            "    Definir a, b Como Entero;",
            "    Leer a;",
            "    Leer b;",
            "    Escribir a + b;",
            "FinAlgoritmo",
            "",
        ]
    )
    imported = workspace_from_source(source)
    assert imported.workspace is not None
    checked = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/check/",
        {"workspace": imported.workspace, "tool": "diagrama"},
        format="json",
    )
    assert checked.status_code == 200, checked.content
    assert checked.json()["passed"] is True
    assert checked.json()["attempt"]["next_stage"] == "lenguaje"
    program = "n1 = int(input())\nn2 = int(input())\nprint(n1 + n2)\n"
    missed = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/language/",
        {"language": "python", "source": program, "outputs": ["8\n", "30\n", "1\n"]},
        format="json",
    )
    assert missed.status_code == 200, missed.content
    assert missed.json()["passed"] is False
    assert missed.json()["percent"] == 66
    sent = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/language/",
        {"language": "python", "source": program},
        format="json",
    )
    assert sent.status_code == 200, sent.content
    assert sent.json()["passed"] is True
    assert sent.json()["percent"] == 100
    assert [item["output"] for item in sent.json()["cases"]] == ["8\n", "30\n", "0\n"]
    assert sent.json()["attempt"]["next_stage"] == "explicar"
    graded = checked.json()["attempt"]["cases"]
    assert [item["passed"] for item in graded] == [True, True, True]
    assert graded[0]["output"].endswith("8\n")
    closed = client.post(
        f"/api/v1/learning/attempts/{attempt_id}/close/",
        {"reflection": "Se leen los dos enteros y se escribe su suma."},
        format="json",
    )
    assert closed.status_code == 200, closed.content
    solution = closed.json()["attempt"]["solution"]
    assert solution["tool"] == "diagrama"
    assert "a + b" in solution["source"]
    assert "blocks" not in solution
    assert "print(n1 + n2)" in solution["language"]["source"]
    assert solution["language"]["percent"] == 100
