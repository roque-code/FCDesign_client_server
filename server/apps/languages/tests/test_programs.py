"""Programas guardados en Lenguajes y la revisión del docente."""

import pytest
from rest_framework.test import APIClient

from apps.billing.models import Plan
from apps.tests.helpers import refresh_csrf, register

pytestmark = pytest.mark.django_db


def _browser() -> APIClient:
    client = APIClient(enforce_csrf_checks=True, HTTP_X_AULIVANA_FCDDESIGN_CLIENT="")
    refresh_csrf(client)
    return client


def _enable_languages() -> None:
    plan = Plan.objects.get(audience="student", code="premium")
    plan.features = {**plan.features, "languages": True}
    plan.save(update_fields=["features"])


def _student(email: str) -> tuple[APIClient, int]:
    client = _browser()
    created = register(client, email=email, display_name="Alumno")
    assert created.status_code == 201, created.content
    return client, created.json()["id"]


def test_sin_la_opcion_no_se_guardan_programas():
    client, _ = _student("programa.cerrado@ejemplo.test")
    denied = client.post(
        "/api/v1/languages/programs/",
        {"name": "Hola", "language": "python", "source": "print(1)\n"},
        format="json",
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "plan_forbidden"


def test_el_alumno_guarda_abre_cambia_y_borra_un_programa():
    _enable_languages()
    client, _ = _student("programa.alumno@ejemplo.test")

    created = client.post(
        "/api/v1/languages/programs/",
        {"name": "  Hola  ", "language": "python", "source": 'print("hola")\n'},
        format="json",
    )
    assert created.status_code == 201, created.content
    program = created.json()
    assert program["name"] == "Hola"
    assert program["source"] == 'print("hola")\n'

    same_name_other_language = client.post(
        "/api/v1/languages/programs/",
        {"name": "Hola", "language": "java", "source": ""},
        format="json",
    )
    assert same_name_other_language.status_code == 201

    repeated = client.post(
        "/api/v1/languages/programs/",
        {"name": "Hola", "language": "python", "source": ""},
        format="json",
    )
    assert repeated.status_code == 409

    unknown = client.post(
        "/api/v1/languages/programs/",
        {"name": "Otro", "language": "cobol", "source": ""},
        format="json",
    )
    assert unknown.status_code == 400

    listed = client.get("/api/v1/languages/programs/").json()["results"]
    assert [(row["language"], row["name"]) for row in listed] == [
        ("java", "Hola"),
        ("python", "Hola"),
    ]
    assert "source" not in listed[0]

    url = f"/api/v1/languages/programs/{program['id']}/"
    changed = client.patch(url, {"source": "print(2)\n"}, format="json")
    assert changed.status_code == 200
    assert client.get(url).json()["source"] == "print(2)\n"

    renamed = client.patch(url, {"name": "Saludo"}, format="json")
    assert renamed.json()["name"] == "Saludo"

    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404


def test_un_alumno_no_abre_el_programa_de_otro():
    _enable_languages()
    owner, _ = _student("programa.dueno@ejemplo.test")
    program = owner.post(
        "/api/v1/languages/programs/",
        {"name": "Mio", "language": "c", "source": "int main(){}\n"},
        format="json",
    ).json()
    other, _ = _student("programa.ajeno@ejemplo.test")
    url = f"/api/v1/languages/programs/{program['id']}/"
    assert other.get(url).status_code == 404
    assert other.patch(url, {"source": ""}, format="json").status_code == 404
    assert other.delete(url).status_code == 404
    assert owner.get(url).json()["source"] == "int main(){}\n"


def test_el_docente_ve_los_programas_de_sus_alumnos():
    _enable_languages()
    student, student_id = _student("programa.grupo@ejemplo.test")
    student.post(
        "/api/v1/languages/programs/",
        {"name": "Tarea", "language": "python", "source": "print(3)\n"},
        format="json",
    )

    teacher = _browser()
    register(teacher, email="programa.profe@ejemplo.test", display_name="Profe", role="teacher")
    url = f"/api/v1/classroom/students/{student_id}/programs/"
    assert teacher.get(url).status_code == 404

    community = teacher.post("/api/v1/communities/", {"name": "Lenguajes"}, format="json")
    assert community.status_code == 201, community.content
    added = teacher.post(
        f"/api/v1/communities/{community.json()['id']}/members/",
        {"user_id": student_id},
        format="json",
    )
    assert added.status_code in (200, 201), added.content

    seen = teacher.get(url)
    assert seen.status_code == 200, seen.content
    assert seen.json()["student"]["id"] == student_id
    assert [(row["name"], row["source"]) for row in seen.json()["programs"]] == [
        ("Tarea", "print(3)\n")
    ]

    stranger = _browser()
    register(stranger, email="programa.ajena@ejemplo.test", display_name="Otra", role="teacher")
    assert stranger.get(url).status_code == 404
    assert student.get(url).status_code == 403
