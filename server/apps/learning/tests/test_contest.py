"""La práctica de concurso trae 50 programas y el CSV crea retos de los cuatro tipos."""

import pytest
from rest_framework.test import APIClient

from apps.learning.contest_data import (
    CONTEST_BANK_NAME,
    CONTEST_ROUTE_NAME,
    build_contest,
)
from apps.learning.csv_import import template_csv
from apps.learning.models import Challenge, PathEntry
from apps.tests.helpers import register

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


def test_el_formato_rechaza_un_tipo_desconocido():
    teacher = APIClient()
    register(teacher, email="csv-tipo@ejemplo.test", display_name="Profe Tipo", role="teacher")
    response = teacher.get("/api/v1/learning/challenges/csv/?tipo=dibujo")
    assert response.status_code == 400
