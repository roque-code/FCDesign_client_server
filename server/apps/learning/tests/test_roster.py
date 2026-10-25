"""Un docente lee el avance de las cuentas de sus comunidades."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Profile
from apps.learning.bank_data import ROUTE_NAME
from apps.learning.models import Challenge, ChallengeAttempt, Reflection, WorkspaceSnapshot
from apps.tests.helpers import register

pytestmark = pytest.mark.django_db


def _teacher(email: str, name: str) -> APIClient:
    client = APIClient()
    register(client, email=email, display_name=name, role="teacher")
    return client


def test_el_alumno_no_lee_el_avance():
    student = APIClient()
    register(student, email="alumno-fase8@ejemplo.test", display_name="Alumno Fase")
    denied = student.get("/api/v1/learning/roster/")
    assert denied.status_code == 403
    hidden = student.get("/api/v1/learning/roster/1/")
    assert hidden.status_code == 403


def test_el_docente_ve_solo_a_quien_ya_puede_ver():
    teacher = _teacher("profe-fase8@ejemplo.test", "Profe Fase")
    other = _teacher("otra-fase8@ejemplo.test", "Otra Fase")
    student = APIClient()
    created = register(student, email="en-grupo@ejemplo.test", display_name="En Grupo")
    outsider = APIClient()
    outside = register(outsider, email="fuera-grupo@ejemplo.test", display_name="Fuera")
    student_id = created.json()["id"]
    outside_id = outside.json()["id"]

    community = teacher.post("/api/v1/communities/", {"name": "Grupo A"}, format="json")
    assert community.status_code == 201, community.content
    added = teacher.post(
        f"/api/v1/communities/{community.json()['id']}/members/",
        {"user_id": student_id},
        format="json",
    )
    assert added.status_code == 201, added.content

    empty = other.get("/api/v1/learning/roster/")
    assert empty.status_code == 200
    assert empty.json()["routes"] == []
    assert other.get(f"/api/v1/learning/roster/{student_id}/").status_code == 404
    assert teacher.get(f"/api/v1/learning/roster/{outside_id}/").status_code == 404

    challenge = (
        Challenge.objects.filter(is_published=True).order_by("unit__position", "position").first()
    )
    assert challenge is not None
    user = get_user_model().objects.get(pk=student_id)
    ChallengeAttempt.objects.create(
        user=user,
        challenge=challenge,
        status=ChallengeAttempt.COMPLETED,
        score=80,
        summary="Puntuación 80.",
        finished_at=timezone.now(),
    )
    Profile.objects.filter(user=user).update(points=challenge.points)

    roster = teacher.get("/api/v1/learning/roster/")
    assert roster.status_code == 200
    routes = roster.json()["routes"]
    fundamentos_list = next(item for item in routes if item["name"] == "Fundamentos")
    assert [item["id"] for item in fundamentos_list["students"]] == [student_id]
    person = fundamentos_list["students"][0]
    assert person["display_name"] == "En Grupo"
    assert person["completed"] == 1
    assert person["points"] == challenge.points
    assert person["communities"] == ["Grupo A"]
    assert person["total"] >= 1

    detail = teacher.get(f"/api/v1/learning/roster/{student_id}/")
    assert detail.status_code == 200, detail.content
    body = detail.json()
    fundamentos = next(item for item in body["paths"] if item["name"] == "Fundamentos")
    done = next(item for item in fundamentos["challenges"] if item["id"] == str(challenge.id))
    assert done["state"] == "completed"
    assert done["score"] == 80
    assert [item["name"] for item in routes] == ["Fundamentos", ROUTE_NAME]
    assert body["person"]["rank"] >= 1
    leaked = detail.content.decode()
    assert "workspace" not in leaked
    assert "reflection" not in leaked
    assert "Esta es la solución explicada" not in leaked

    created_path = teacher.post(
        "/api/v1/learning/authored/",
        {"name": "Repaso grupo", "description": "Para el grupo"},
        format="json",
    )
    assert created_path.status_code == 201, created_path.content
    path_id = created_path.json()["id"]
    placed = teacher.put(
        f"/api/v1/learning/authored/{path_id}/challenges/",
        {"challenge_ids": [str(challenge.id)]},
        format="json",
    )
    assert placed.status_code == 200, placed.content
    assigned = teacher.put(
        f"/api/v1/learning/authored/{path_id}/assignments/",
        {"community_ids": [community.json()["id"]], "student_ids": []},
        format="json",
    )
    assert assigned.status_code == 200, assigned.content
    private = teacher.post(
        "/api/v1/learning/authored/",
        {"name": "Sin asignar", "description": ""},
        format="json",
    )
    assert private.status_code == 201, private.content

    other_student = APIClient()
    other_created = register(
        other_student, email="otro-grupo@ejemplo.test", display_name="Otro Alumno"
    )
    other_id = other_created.json()["id"]
    other_community = teacher.post("/api/v1/communities/", {"name": "Grupo B"}, format="json")
    assert other_community.status_code == 201, other_community.content
    other_added = teacher.post(
        f"/api/v1/communities/{other_community.json()['id']}/members/",
        {"user_id": other_id},
        format="json",
    )
    assert other_added.status_code == 201, other_added.content

    grouped = teacher.get("/api/v1/learning/roster/").json()
    by_name = {item["name"]: item for item in grouped["routes"]}
    assert "Sin asignar" not in by_name
    assert [item["id"] for item in by_name["Repaso grupo"]["students"]] == [student_id]
    assert by_name["Repaso grupo"]["students"][0]["completed"] == 1
    assert by_name["Repaso grupo"]["students"][0]["total"] == 1
    assert sorted(item["id"] for item in by_name["Fundamentos"]["students"]) == sorted(
        [student_id, other_id]
    )

    again = teacher.get(f"/api/v1/learning/roster/{student_id}/").json()
    names = [item["name"] for item in again["paths"]]
    assert names == ["Fundamentos", ROUTE_NAME, "Repaso grupo"]
    custom = next(item for item in again["paths"] if item["name"] == "Repaso grupo")
    assert custom["completed"] == 1
    assert custom["total"] == 1
    assert custom["challenges"][0]["state"] == "completed"
    assert custom["challenges"][0]["score"] == 80


def test_el_docente_lee_la_respuesta_y_el_codigo():
    teacher = _teacher("profe-trabajo@ejemplo.test", "Profe Trabajo")
    outsider = _teacher("ajena-trabajo@ejemplo.test", "Ajena")
    student = APIClient()
    created = register(student, email="trabajo@ejemplo.test", display_name="Con Trabajo")
    student_id = created.json()["id"]
    community = teacher.post("/api/v1/communities/", {"name": "Grupo trabajo"}, format="json")
    assert community.status_code == 201, community.content
    added = teacher.post(
        f"/api/v1/communities/{community.json()['id']}/members/",
        {"user_id": student_id},
        format="json",
    )
    assert added.status_code == 201, added.content

    challenge = (
        Challenge.objects.filter(is_published=True, activity_type=Challenge.BUILD)
        .order_by("unit__position", "position")
        .first()
    )
    assert challenge is not None
    user = get_user_model().objects.get(pk=student_id)
    attempt = ChallengeAttempt.objects.create(
        user=user,
        challenge=challenge,
        status=ChallengeAttempt.COMPLETED,
        score=90,
        summary="Puntuación 90.",
        elapsed_seconds=80,
        finished_at=timezone.now(),
    )
    WorkspaceSnapshot.objects.create(
        attempt=attempt,
        schema_version=2,
        blockly_json={"stage": "razonar", "answer": {"text": "15"}},
    )
    WorkspaceSnapshot.objects.create(
        attempt=attempt,
        schema_version=1,
        pseudocode="Algoritmo Laboratorio\nEscribir 1;\nFinAlgoritmo\n",
    )
    WorkspaceSnapshot.objects.create(
        attempt=attempt,
        schema_version=2,
        blockly_json={
            "stage": "lenguaje",
            "mark": 2,
            "answer": {
                "language": "python",
                "source": "print('hola')\n",
                "outputs": ["hola\n"],
                "passed": True,
                "percent": 100,
            },
        },
    )
    Reflection.objects.create(attempt=attempt, body="Expliqué el resultado del reto.")

    hidden = student.get(f"/api/v1/learning/roster/{student_id}/challenges/{challenge.id}/")
    assert hidden.status_code == 403
    assert (
        outsider.get(f"/api/v1/learning/roster/{student_id}/challenges/{challenge.id}/").status_code
        == 404
    )

    work = teacher.get(f"/api/v1/learning/roster/{student_id}/challenges/{challenge.id}/")
    assert work.status_code == 200, work.content
    body = work.json()
    assert body["challenge"]["id"] == str(challenge.id)
    assert body["challenge"]["prompt"] == challenge.prompt
    assert body["attempt"]["score"] == 90
    assert body["attempt"]["answer"] == [{"label": "Respuesta", "value": "15"}]
    assert body["attempt"]["source"].startswith("Algoritmo Laboratorio")
    assert body["attempt"]["solution"]["tool"] == "codigo"
    assert body["attempt"]["solution"]["source"].startswith("Algoritmo Laboratorio")
    assert body["attempt"]["solution"]["language"]["source"] == "print('hola')\n"
    assert body["attempt"]["solution"]["language"]["percent"] == 100
    assert body["attempt"]["language"]["language"] == "python"
    assert "blocks" not in body["attempt"]["solution"]
    assert body["attempt"]["reflection"] == "Expliqué el resultado del reto."
    leaked = work.content.decode()
    assert "workspace" not in leaked
    assert "Esta es la solución explicada" not in leaked
    assert "blockly" not in leaked
