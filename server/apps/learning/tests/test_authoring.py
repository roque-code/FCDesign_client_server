"""Un docente crea una ruta y la asigna a comunidades o a un alumno."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Profile
from apps.learning.models import Challenge, ChallengeAttempt
from apps.tests.helpers import register

pytestmark = pytest.mark.django_db


def _teacher(email: str, name: str) -> APIClient:
    client = APIClient()
    register(client, email=email, display_name=name, role="teacher")
    return client


def _student(email: str, name: str) -> tuple[APIClient, int]:
    client = APIClient()
    created = register(client, email=email, display_name=name)
    return client, created.json()["id"]


def _catalog_ids() -> list[str]:
    rows = Challenge.objects.filter(is_published=True, unit__path__owner__isnull=True).order_by(
        "unit__position", "position"
    )[:2]
    return [str(item.id) for item in rows]


def test_un_alumno_no_arma_rutas():
    student, _student_id = _student("ruta-alumno@ejemplo.test", "Alumno Ruta")
    denied = student.post("/api/v1/learning/authored/", {"name": "Mia"}, format="json")
    assert denied.status_code == 403
    assert student.get("/api/v1/learning/catalog/").status_code == 403


def test_el_docente_asigna_la_ruta_a_una_comunidad_y_a_un_alumno():
    teacher = _teacher("ruta-profe@ejemplo.test", "Profe Ruta")
    other = _teacher("ruta-otra@ejemplo.test", "Otra Ruta")
    member, member_id = _student("ruta-miembro@ejemplo.test", "Miembro")
    chosen, chosen_id = _student("ruta-elegido@ejemplo.test", "Elegido")
    partner, partner_id = _student("ruta-pareja@ejemplo.test", "Pareja")
    outsider, outsider_id = _student("ruta-fuera@ejemplo.test", "Fuera")
    ids = _catalog_ids()
    assert len(ids) == 2

    created = teacher.post(
        "/api/v1/learning/authored/",
        {"name": "Repaso", "description": "Dos retos"},
        format="json",
    )
    assert created.status_code == 201, created.content
    path_id = created.json()["id"]
    assert created.json()["is_published"] is False

    placed = teacher.put(
        f"/api/v1/learning/authored/{path_id}/challenges/",
        {"challenge_ids": [ids[1], ids[0]]},
        format="json",
    )
    assert placed.status_code == 200, placed.content
    assert [item["id"] for item in placed.json()["challenges"]] == [ids[1], ids[0]]

    group = teacher.post("/api/v1/communities/", {"name": "Grupo Ruta"}, format="json")
    assert group.status_code == 201, group.content
    community_id = group.json()["id"]
    assert (
        teacher.post(
            f"/api/v1/communities/{community_id}/members/",
            {"user_id": member_id},
            format="json",
        ).status_code
        == 201
    )
    other_group = other.post("/api/v1/communities/", {"name": "Ajena"}, format="json")
    foreign = teacher.put(
        f"/api/v1/learning/authored/{path_id}/assignments/",
        {"community_ids": [other_group.json()["id"]], "student_ids": []},
        format="json",
    )
    assert foreign.status_code == 404

    missing_student = teacher.put(
        f"/api/v1/learning/authored/{path_id}/assignments/",
        {"community_ids": [], "student_ids": [outsider_id]},
        format="json",
    )
    assert missing_student.status_code == 404

    pair = teacher.post("/api/v1/communities/", {"name": "Pareja"}, format="json")
    assert pair.status_code == 201, pair.content
    pair_id = pair.json()["id"]
    assert (
        teacher.post(
            f"/api/v1/communities/{pair_id}/members/",
            {"user_id": chosen_id},
            format="json",
        ).status_code
        == 201
    )
    assert (
        teacher.post(
            f"/api/v1/communities/{pair_id}/members/",
            {"user_id": partner_id},
            format="json",
        ).status_code
        == 201
    )
    assigned = teacher.put(
        f"/api/v1/learning/authored/{path_id}/assignments/",
        {"community_ids": [community_id], "student_ids": [chosen_id]},
        format="json",
    )
    assert assigned.status_code == 200, assigned.content
    assert assigned.json()["is_published"] is True
    assert assigned.json()["communities"] == [{"id": community_id, "name": "Grupo Ruta"}]
    assert assigned.json()["students"][0]["id"] == chosen_id
    listed = teacher.get("/api/v1/learning/authored/").json()["results"]
    summary = next(item for item in listed if item["name"] == "Repaso")
    assert summary["community_count"] == 1
    assert summary["student_count"] == 2

    assert (
        other.patch(
            f"/api/v1/learning/authored/{path_id}/",
            {"name": "Robada"},
            format="json",
        ).status_code
        == 404
    )

    def titles(client):
        response = client.get("/api/v1/learning/paths/")
        assert response.status_code == 200, response.content
        return {item["name"]: item for item in response.json()["results"]}

    seen = titles(member)
    assert "Fundamentos" in seen
    assert [item["id"] for item in seen["Repaso"]["challenges"]] == [ids[1], ids[0]]
    assert seen["Repaso"]["challenges"][0]["state"] == "available"
    assert seen["Repaso"]["challenges"][1]["state"] == "locked"
    assert "Repaso" in titles(chosen)
    assert "Repaso" not in titles(partner)
    assert "Repaso" not in titles(outsider)
    assert titles(outsider)["Fundamentos"]["name"] == "Fundamentos"
    assert member.get("/api/v1/learning/path/").json()["name"] == "Fundamentos"

    first = Challenge.objects.get(pk=ids[1])
    ChallengeAttempt.objects.create(
        user_id=member_id,
        challenge=first,
        status=ChallengeAttempt.COMPLETED,
        score=90,
        finished_at=timezone.now(),
    )
    again = titles(member)["Repaso"]["challenges"]
    assert again[0]["state"] == "completed"
    assert again[1]["state"] == "available"

    opened = member.post(
        f"/api/v1/learning/challenges/{ids[0]}/attempts/",
        {"path_id": path_id},
        format="json",
    )
    assert opened.status_code == 200, opened.content
    blocked = outsider.post(
        f"/api/v1/learning/challenges/{ids[0]}/attempts/",
        {"path_id": path_id},
        format="json",
    )
    assert blocked.status_code == 404


def test_el_horario_del_reto_se_puede_cambiar_y_limita_el_inicio():
    teacher = _teacher("horario-profe@ejemplo.test", "Profe Horario")
    student, _student_id = _student("horario-alumno@ejemplo.test", "Alumno Horario")
    ids = _catalog_ids()
    created = teacher.post(
        "/api/v1/learning/authored/",
        {"name": "Con horario", "description": ""},
        format="json",
    )
    assert created.status_code == 201, created.content
    path_id = created.json()["id"]
    placed = teacher.put(
        f"/api/v1/learning/authored/{path_id}/challenges/",
        {"challenge_ids": ids},
        format="json",
    )
    assert placed.status_code == 200, placed.content
    community = teacher.post("/api/v1/communities/", {"name": "Grupo Horario"}, format="json")
    assert community.status_code == 201, community.content
    assert (
        teacher.post(
            f"/api/v1/communities/{community.json()['id']}/members/",
            {"user_id": _student_id},
            format="json",
        ).status_code
        == 201
    )
    assert (
        teacher.put(
            f"/api/v1/learning/authored/{path_id}/assignments/",
            {"community_ids": [community.json()["id"]], "student_ids": []},
            format="json",
        ).status_code
        == 200
    )

    later = timezone.now() + timedelta(days=2)
    sooner = timezone.now() - timedelta(days=1)
    denied = student.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{ids[0]}/",
        {"opens_at": later.isoformat()},
        format="json",
    )
    assert denied.status_code == 403
    invalid = teacher.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{ids[0]}/",
        {"opens_at": later.isoformat(), "closes_at": sooner.isoformat()},
        format="json",
    )
    assert invalid.status_code == 400

    scheduled = teacher.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{ids[0]}/",
        {"opens_at": later.isoformat(), "closes_at": None},
        format="json",
    )
    assert scheduled.status_code == 200, scheduled.content
    first = next(item for item in scheduled.json()["challenges"] if item["id"] == ids[0])
    assert first["opens_at"] is not None
    assert first["closes_at"] is None
    assert first["withdrawn"] is False

    def student_path():
        rows = student.get("/api/v1/learning/paths/").json()["results"]
        return next(item for item in rows if item["name"] == "Con horario")

    assert student_path()["challenges"][0]["state"] == "scheduled"
    assert student_path()["challenges"][1]["state"] == "available"
    early = student.post(
        f"/api/v1/learning/challenges/{ids[0]}/attempts/",
        {"path_id": path_id},
        format="json",
    )
    assert early.status_code == 403

    reordered = teacher.put(
        f"/api/v1/learning/authored/{path_id}/challenges/",
        {"challenge_ids": [ids[1], ids[0]]},
        format="json",
    )
    assert reordered.status_code == 200, reordered.content
    moved = next(item for item in reordered.json()["challenges"] if item["id"] == ids[0])
    assert moved["opens_at"] == first["opens_at"]
    teacher.put(
        f"/api/v1/learning/authored/{path_id}/challenges/",
        {"challenge_ids": ids},
        format="json",
    )

    opened = teacher.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{ids[0]}/",
        {"opens_at": None, "closes_at": (timezone.now() + timedelta(hours=2)).isoformat()},
        format="json",
    )
    assert opened.status_code == 200, opened.content
    assert student_path()["challenges"][0]["state"] == "available"
    assert (
        student.post(
            f"/api/v1/learning/challenges/{ids[0]}/attempts/",
            {"path_id": path_id},
            format="json",
        ).status_code
        == 200
    )

    closed = teacher.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{ids[1]}/",
        {"closes_at": sooner.isoformat()},
        format="json",
    )
    assert closed.status_code == 200, closed.content
    assert (
        next(item for item in student_path()["challenges"] if item["id"] == ids[1])["state"]
        == "closed"
    )
    ChallengeAttempt.objects.create(
        user_id=_student_id,
        challenge_id=ids[0],
        status=ChallengeAttempt.COMPLETED,
        score=70,
        finished_at=timezone.now(),
    )
    assert (
        next(item for item in student_path()["challenges"] if item["id"] == ids[1])["state"]
        == "closed"
    )
    late = student.post(
        f"/api/v1/learning/challenges/{ids[1]}/attempts/",
        {"path_id": path_id},
        format="json",
    )
    assert late.status_code == 403

    hidden = teacher.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{ids[1]}/",
        {"withdrawn": True},
        format="json",
    )
    assert hidden.status_code == 200, hidden.content
    assert (
        next(item for item in hidden.json()["challenges"] if item["id"] == ids[1])["withdrawn"]
        is True
    )
    assert [item["id"] for item in student_path()["challenges"]] == [ids[0]]


def test_un_reto_con_horario_no_espera_a_los_ligados():
    teacher = _teacher("libre-profe@ejemplo.test", "Profe Libre")
    student, student_id = _student("libre-alumno@ejemplo.test", "Alumno Libre")
    ids = [
        str(item.id)
        for item in Challenge.objects.filter(
            is_published=True, unit__path__owner__isnull=True
        ).order_by("unit__position", "position")[:3]
    ]
    assert len(ids) == 3
    created = teacher.post(
        "/api/v1/learning/authored/",
        {"name": "Mixta", "description": ""},
        format="json",
    )
    path_id = created.json()["id"]
    assert (
        teacher.put(
            f"/api/v1/learning/authored/{path_id}/challenges/",
            {"challenge_ids": ids},
            format="json",
        ).status_code
        == 200
    )
    community = teacher.post("/api/v1/communities/", {"name": "Grupo Libre"}, format="json")
    assert (
        teacher.post(
            f"/api/v1/communities/{community.json()['id']}/members/",
            {"user_id": student_id},
            format="json",
        ).status_code
        == 201
    )
    assert (
        teacher.put(
            f"/api/v1/learning/authored/{path_id}/assignments/",
            {"community_ids": [community.json()["id"]], "student_ids": []},
            format="json",
        ).status_code
        == 200
    )
    window = teacher.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{ids[1]}/",
        {
            "opens_at": (timezone.now() - timedelta(hours=1)).isoformat(),
            "closes_at": (timezone.now() + timedelta(days=1)).isoformat(),
        },
        format="json",
    )
    assert window.status_code == 200, window.content

    listed = student.get("/api/v1/learning/paths/").json()["results"]
    challenges = next(item for item in listed if item["name"] == "Mixta")["challenges"]
    by_id = {item["id"]: item["state"] for item in challenges}
    assert by_id[ids[0]] == "available"
    assert by_id[ids[1]] == "available"
    assert by_id[ids[2]] == "locked"
    opened = student.post(
        f"/api/v1/learning/challenges/{ids[1]}/attempts/",
        {"path_id": path_id},
        format="json",
    )
    assert opened.status_code == 200, opened.content

    ChallengeAttempt.objects.create(
        user_id=student_id,
        challenge_id=ids[0],
        status=ChallengeAttempt.COMPLETED,
        score=80,
        finished_at=timezone.now(),
    )
    again = student.get("/api/v1/learning/paths/").json()["results"]
    states = {
        item["id"]: item["state"]
        for item in next(row for row in again if row["name"] == "Mixta")["challenges"]
    }
    assert states[ids[2]] == "available"


def test_retirar_un_reto_resuelto_conserva_puntos_y_avance():
    teacher = _teacher("retira-profe@ejemplo.test", "Profe Retira")
    solved, solved_id = _student("retira-listo@ejemplo.test", "Ya lo hizo")
    waiting, waiting_id = _student("retira-pendiente@ejemplo.test", "Todavía no")
    ids = _catalog_ids()
    created = teacher.post(
        "/api/v1/learning/authored/",
        {"name": "Con retiro", "description": ""},
        format="json",
    )
    path_id = created.json()["id"]
    assert (
        teacher.put(
            f"/api/v1/learning/authored/{path_id}/challenges/",
            {"challenge_ids": ids},
            format="json",
        ).status_code
        == 200
    )
    community = teacher.post("/api/v1/communities/", {"name": "Grupo Retiro"}, format="json")
    for user_id in (solved_id, waiting_id):
        assert (
            teacher.post(
                f"/api/v1/communities/{community.json()['id']}/members/",
                {"user_id": user_id},
                format="json",
            ).status_code
            == 201
        )
    assert (
        teacher.put(
            f"/api/v1/learning/authored/{path_id}/assignments/",
            {"community_ids": [community.json()["id"]], "student_ids": []},
            format="json",
        ).status_code
        == 200
    )

    challenge = Challenge.objects.get(pk=ids[1])
    ChallengeAttempt.objects.create(
        user_id=solved_id,
        challenge=challenge,
        status=ChallengeAttempt.COMPLETED,
        score=80,
        summary="Puntuación 80.",
        finished_at=timezone.now(),
    )
    Profile.objects.filter(user_id=solved_id).update(points=challenge.points)
    hidden = teacher.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{ids[1]}/",
        {"withdrawn": True},
        format="json",
    )
    assert hidden.status_code == 200, hidden.content
    assert Profile.objects.get(user_id=solved_id).points == challenge.points

    def challenges_of(client):
        rows = client.get("/api/v1/learning/paths/").json()["results"]
        return next(item for item in rows if item["name"] == "Con retiro")["challenges"]

    kept = challenges_of(solved)
    assert [item["id"] for item in kept] == ids
    done = next(item for item in kept if item["id"] == ids[1])
    assert done["state"] == "completed"
    assert done["withdrawn"] is True
    review = solved.post(
        f"/api/v1/learning/challenges/{ids[1]}/attempts/",
        {"path_id": path_id},
        format="json",
    )
    assert review.status_code == 200, review.content
    assert review.json()["attempt"]["status"] == "completed"
    assert review.json()["attempt"]["score"] == 80
    assert review.json()["attempt"]["summary"] == "Puntuación 80."
    assert review.json()["points"] == challenge.points

    assert [item["id"] for item in challenges_of(waiting)] == [ids[0]]
    assert (
        waiting.post(
            f"/api/v1/learning/challenges/{ids[1]}/attempts/",
            {"path_id": path_id},
            format="json",
        ).status_code
        == 404
    )

    roster = teacher.get("/api/v1/learning/roster/").json()["routes"]
    students = next(item for item in roster if item["name"] == "Con retiro")["students"]
    by_id = {item["id"]: item for item in students}
    assert by_id[solved_id]["completed"] == 1
    assert by_id[solved_id]["total"] == 2
    assert by_id[waiting_id]["completed"] == 0
    assert by_id[waiting_id]["total"] == 1


def test_el_docente_crea_y_edita_un_reto():
    teacher = _teacher("reto-profe@ejemplo.test", "Profe Reto")
    other = _teacher("reto-otro@ejemplo.test", "Otro Reto")
    student, student_id = _student("reto-alumno@ejemplo.test", "Alumno Reto")
    denied = student.post(
        "/api/v1/learning/authored/challenges/",
        {"title": "No"},
        format="json",
    )
    assert denied.status_code == 403

    created = teacher.post(
        "/api/v1/learning/authored/challenges/",
        {
            "title": "Clasifica señales",
            "prompt": "Separa cada frase.",
            "activity_type": "classify",
            "concept": "io",
            "difficulty": 2,
            "points": 20,
            "categories": ["entrada", "salida"],
            "items": [
                {"text": "Leer el nombre", "category": "entrada"},
                {"text": "Mostrar el nombre", "category": "salida"},
            ],
            "hint": "Fíjate quién produce el dato.",
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    challenge_id = created.json()["id"]
    assert created.json()["owned"] is True
    assert created.json()["items"][0]["category"] == "entrada"
    assert created.json()["hints"] == ["Fíjate quién produce el dato."]

    catalog = teacher.get("/api/v1/learning/catalog/").json()
    own = next(item for item in catalog["results"] if item["id"] == challenge_id)
    assert own["owned"] is True
    assert any(item["key"] == "io" for item in catalog["concepts"])
    names = [item["name"] for item in teacher.get("/api/v1/learning/paths/").json()["results"]]
    assert all(not name.startswith("banco interno") for name in names)

    edited = teacher.patch(
        f"/api/v1/learning/authored/challenges/{challenge_id}/",
        {
            "title": "Clasifica mejor",
            "prompt": "Separa cada frase.",
            "activity_type": "classify",
            "concept": "io",
            "difficulty": 2,
            "points": 20,
            "categories": ["entrada", "salida"],
            "items": [
                {"text": "Leer el nombre", "category": "entrada"},
                {"text": "Mostrar el nombre", "category": "salida"},
            ],
            "hints": ["Primera pista.", "Segunda pista."],
        },
        format="json",
    )
    assert edited.status_code == 200, edited.content
    assert edited.json()["title"] == "Clasifica mejor"
    assert edited.json()["hints"] == ["Primera pista.", "Segunda pista."]
    too_many = teacher.post(
        "/api/v1/learning/authored/challenges/",
        {
            "title": "Demasiadas pistas",
            "prompt": "Separa cada frase.",
            "activity_type": "classify",
            "concept": "io",
            "categories": ["entrada", "salida"],
            "items": [
                {"text": "Leer el nombre", "category": "entrada"},
                {"text": "Mostrar el nombre", "category": "salida"},
            ],
            "hints": ["uno", "dos", "tres", "cuatro", "cinco", "seis"],
        },
        format="json",
    )
    assert too_many.status_code == 400, too_many.content
    built = teacher.post(
        "/api/v1/learning/authored/challenges/",
        {
            "title": "El doble",
            "prompt": "Lee un entero y escribe su doble.",
            "activity_type": "build",
            "concept": "operator",
            "question": "¿Qué símbolo multiplica?",
            "accepted": ["*"],
            "inputs": ["6"],
            "expected_output": "12",
            "allowed_blocks": ["traza_definir", "traza_escribir", "traza_definir"],
        },
        format="json",
    )
    assert built.status_code == 201, built.content
    assert built.json()["allowed_blocks"] == ["traza_definir", "traza_escribir"]
    assert built.json()["tools"] == ["bloques"]
    assert built.json()["cases"] == [
        {"name": "esperado", "inputs": ["6"], "expected_output": "12\n"}
    ]
    measured = teacher.post(
        "/api/v1/learning/authored/challenges/",
        {
            "title": "El doble medido",
            "prompt": "Lee un entero y escribe su doble.",
            "activity_type": "build",
            "concept": "operator",
            "question": "¿Qué símbolo multiplica?",
            "accepted": ["*"],
            "tools": ["codigo", "diagrama", "bloques"],
            "cases": [
                {"inputs": ["6"], "expected_output": "12"},
                {"inputs": ["0"], "expected_output": "0"},
            ],
            "allowed_blocks": ["traza_definir", "traza_leer", "traza_escribir", "traza_entero"],
        },
        format="json",
    )
    assert measured.status_code == 201, measured.content
    assert measured.json()["tools"] == ["codigo", "diagrama", "bloques"]
    assert [item["name"] for item in measured.json()["cases"]] == ["Caso 1", "Caso 2"]
    assert measured.json()["cases"][1]["inputs"] == ["0"]
    assert measured.json()["cases"][1]["expected_output"] == "0\n"
    unknown = teacher.post(
        "/api/v1/learning/authored/challenges/",
        {
            "title": "Bloque ajeno",
            "prompt": "Lee un entero y escribe su doble.",
            "activity_type": "build",
            "concept": "operator",
            "question": "¿Qué símbolo multiplica?",
            "accepted": ["*"],
            "expected_output": "12",
            "allowed_blocks": ["traza_inventar"],
        },
        format="json",
    )
    assert unknown.status_code == 400, unknown.content
    assert other.get(f"/api/v1/learning/authored/challenges/{challenge_id}/").status_code == 404
    system_id = _catalog_ids()[0]
    assert (
        teacher.patch(
            f"/api/v1/learning/authored/challenges/{system_id}/",
            {"title": "Cambiado", "prompt": "x", "activity_type": "classify", "concept": "io"},
            format="json",
        ).status_code
        == 404
    )
    assert (
        teacher.post(
            "/api/v1/learning/authored/challenges/",
            {
                "title": "Orden corto",
                "prompt": "Ordena.",
                "activity_type": "order",
                "concept": "io",
                "items": ["Solo una"],
            },
            format="json",
        ).status_code
        == 400
    )
    broken = teacher.post(
        "/api/v1/learning/authored/challenges/",
        {
            "title": "Predice mal",
            "prompt": "Anticipa.",
            "activity_type": "predict",
            "concept": "variable",
            "question": "¿Qué se escribe?",
            "accepted": ["4"],
            "source": "esto no es pseudocódigo",
        },
        format="json",
    )
    assert broken.status_code == 400, broken.content

    path = teacher.post("/api/v1/learning/authored/", {"name": "Con reto propio"}, format="json")
    path_id = path.json()["id"]
    placed = teacher.put(
        f"/api/v1/learning/authored/{path_id}/challenges/",
        {"challenge_ids": [challenge_id]},
        format="json",
    )
    assert placed.status_code == 200, placed.content
    assert placed.json()["challenges"][0]["owned"] is True
    group = teacher.post("/api/v1/communities/", {"name": "Grupo Reto"}, format="json")
    community_id = group.json()["id"]
    assert (
        teacher.post(
            f"/api/v1/communities/{community_id}/members/",
            {"user_id": student_id},
            format="json",
        ).status_code
        == 201
    )
    assert (
        teacher.put(
            f"/api/v1/learning/authored/{path_id}/assignments/",
            {"community_ids": [community_id], "student_ids": []},
            format="json",
        ).status_code
        == 200
    )
    started = student.post(
        f"/api/v1/learning/challenges/{challenge_id}/attempts/",
        {"path_id": path_id},
        format="json",
    )
    assert started.status_code == 200, started.content
    task_items = started.json()["challenge"]["task"]["items"]
    assert task_items == [
        {"id": "e1", "text": "Leer el nombre"},
        {"id": "e2", "text": "Mostrar el nombre"},
    ]
    assert "category" not in task_items[0]
    attempt_id = started.json()["attempt"]["id"]
    asked = student.post(f"/api/v1/learning/attempts/{attempt_id}/hint/", {}, format="json")
    assert asked.status_code == 200, asked.content
    kept = teacher.patch(
        f"/api/v1/learning/authored/challenges/{challenge_id}/",
        {
            "title": "Clasifica con pista",
            "prompt": "Separa cada frase.",
            "activity_type": "classify",
            "concept": "io",
            "difficulty": 2,
            "points": 20,
            "categories": ["entrada", "salida"],
            "items": [
                {"text": "Leer el nombre", "category": "entrada"},
                {"text": "Mostrar el nombre", "category": "salida"},
            ],
            "hints": ["Primera pista.", "Segunda pista."],
        },
        format="json",
    )
    assert kept.status_code == 200, kept.content
    assert kept.json()["hints"] == ["Primera pista.", "Segunda pista."]
    removed = teacher.patch(
        f"/api/v1/learning/authored/challenges/{challenge_id}/",
        {
            "title": "Clasifica con pista",
            "prompt": "Separa cada frase.",
            "activity_type": "classify",
            "concept": "io",
            "categories": ["entrada", "salida"],
            "items": [
                {"text": "Leer el nombre", "category": "entrada"},
                {"text": "Mostrar el nombre", "category": "salida"},
            ],
            "hints": [],
        },
        format="json",
    )
    assert removed.status_code == 400, removed.content


def test_el_docente_pone_ponderaciones_en_el_reto_y_en_la_ruta():
    teacher = _teacher("peso-profe@ejemplo.test", "Profe Peso")
    student, student_id = _student("peso-alumno@ejemplo.test", "Alumno Peso")
    custom = {
        "comprension": 40,
        "diseno": 20,
        "correccion": 20,
        "lenguaje": 0,
        "explicacion": 10,
        "autonomia": 10,
    }
    created = teacher.post(
        "/api/v1/learning/authored/challenges/",
        {
            "title": "Clasifica con peso",
            "prompt": "Separa cada frase.",
            "activity_type": "classify",
            "concept": "io",
            "difficulty": 1,
            "points": 10,
            "categories": ["entrada", "salida"],
            "items": [
                {"text": "Leer el nombre", "category": "entrada"},
                {"text": "Mostrar el nombre", "category": "salida"},
            ],
            "weights": custom,
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    assert created.json()["weights"] == custom
    challenge_id = created.json()["id"]
    bad = teacher.patch(
        f"/api/v1/learning/authored/challenges/{challenge_id}/",
        {
            "title": "Clasifica con peso",
            "prompt": "Separa cada frase.",
            "activity_type": "classify",
            "concept": "io",
            "categories": ["entrada", "salida"],
            "items": [
                {"text": "Leer el nombre", "category": "entrada"},
                {"text": "Mostrar el nombre", "category": "salida"},
            ],
            "weights": {**custom, "explicacion": 20},
        },
        format="json",
    )
    assert bad.status_code == 400
    language = teacher.patch(
        f"/api/v1/learning/authored/challenges/{challenge_id}/",
        {
            "title": "Clasifica con peso",
            "prompt": "Separa cada frase.",
            "activity_type": "classify",
            "concept": "io",
            "categories": ["entrada", "salida"],
            "items": [
                {"text": "Leer el nombre", "category": "entrada"},
                {"text": "Mostrar el nombre", "category": "salida"},
            ],
            "weights": {**custom, "correccion": 0, "lenguaje": 20},
        },
        format="json",
    )
    assert language.status_code == 400

    path = teacher.post(
        "/api/v1/learning/authored/",
        {"name": "Ruta con peso", "description": ""},
        format="json",
    )
    assert path.status_code == 201, path.content
    path_id = path.json()["id"]
    placed = teacher.put(
        f"/api/v1/learning/authored/{path_id}/challenges/",
        {"challenge_ids": [challenge_id]},
        format="json",
    )
    assert placed.status_code == 200, placed.content
    assert placed.json()["challenges"][0]["weights"] == custom
    override = {
        "comprension": 10,
        "diseno": 10,
        "correccion": 10,
        "lenguaje": 0,
        "explicacion": 10,
        "autonomia": 60,
    }
    scheduled = teacher.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{challenge_id}/",
        {"weights": override},
        format="json",
    )
    assert scheduled.status_code == 200, scheduled.content
    assert scheduled.json()["challenges"][0]["weights"] == override
    assert scheduled.json()["challenges"][0]["challenge_weights"] == custom

    group = teacher.post("/api/v1/communities/", {"name": "Grupo peso"}, format="json")
    assert group.status_code == 201, group.content
    assert (
        teacher.post(
            f"/api/v1/communities/{group.json()['id']}/members/",
            {"user_id": student_id},
            format="json",
        ).status_code
        == 201
    )
    assert (
        teacher.put(
            f"/api/v1/learning/authored/{path_id}/assignments/",
            {"community_ids": [group.json()["id"]], "student_ids": []},
            format="json",
        ).status_code
        == 200
    )

    started = student.post(
        f"/api/v1/learning/challenges/{challenge_id}/attempts/",
        {"path_id": path_id},
        format="json",
    )
    assert started.status_code == 200, started.content
    attempt_id = started.json()["attempt"]["id"]
    understood = student.post(
        f"/api/v1/learning/attempts/{attempt_id}/stage/",
        {"stage": "comprender", "answer": {"ack": True}},
        format="json",
    )
    assert understood.status_code == 200, understood.content
    assert understood.json()["attempt"]["score"] == 70
    graded = student.post(
        f"/api/v1/learning/attempts/{attempt_id}/stage/",
        {
            "stage": "razonar",
            "answer": {"choices": {"e1": "entrada", "e2": "salida"}},
        },
        format="json",
    )
    assert graded.status_code == 200, graded.content
    assert graded.json()["attempt"]["score"] == 90


def test_el_mismo_reto_se_puede_volver_a_asignar_sin_borrar_el_historial():
    teacher = _teacher("repite-profe@ejemplo.test", "Profe Repite")
    pending, pending_id = _student("repite-pendiente@ejemplo.test", "Pendiente")
    done, done_id = _student("repite-listo@ejemplo.test", "Listo")
    challenge_id = _catalog_ids()[0]
    created = teacher.post(
        "/api/v1/learning/authored/",
        {"name": "Segunda oportunidad", "description": ""},
        format="json",
    )
    assert created.status_code == 201, created.content
    path_id = created.json()["id"]
    placed = teacher.put(
        f"/api/v1/learning/authored/{path_id}/challenges/",
        {"challenge_ids": [challenge_id]},
        format="json",
    )
    assert placed.status_code == 200, placed.content
    entry_id = placed.json()["challenges"][0]["entry_id"]
    past = timezone.now() - timedelta(hours=1)
    opened = timezone.now() - timedelta(hours=2)
    scheduled = teacher.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{challenge_id}/",
        {"entry_id": entry_id, "opens_at": opened.isoformat(), "closes_at": past.isoformat()},
        format="json",
    )
    assert scheduled.status_code == 200, scheduled.content
    community = teacher.post("/api/v1/communities/", {"name": "Grupo Repite"}, format="json")
    assert community.status_code == 201, community.content
    for student_id in (pending_id, done_id):
        assert (
            teacher.post(
                f"/api/v1/communities/{community.json()['id']}/members/",
                {"user_id": student_id},
                format="json",
            ).status_code
            == 201
        )
    assert (
        teacher.put(
            f"/api/v1/learning/authored/{path_id}/assignments/",
            {"community_ids": [community.json()["id"]], "student_ids": []},
            format="json",
        ).status_code
        == 200
    )
    ChallengeAttempt.objects.create(
        user_id=pending_id,
        challenge_id=challenge_id,
        path_id=path_id,
        status=ChallengeAttempt.ABANDONED,
        finished_at=timezone.now(),
    )
    ChallengeAttempt.objects.create(
        user_id=done_id,
        challenge_id=challenge_id,
        path_id=path_id,
        status=ChallengeAttempt.COMPLETED,
        score=80,
        finished_at=timezone.now(),
    )
    before = ChallengeAttempt.objects.filter(challenge_id=challenge_id).count()

    repeated = teacher.put(
        f"/api/v1/learning/authored/{path_id}/challenges/",
        {"challenge_ids": [challenge_id, challenge_id], "entry_ids": [entry_id, None]},
        format="json",
    )
    assert repeated.status_code == 200, repeated.content
    rows = repeated.json()["challenges"]
    assert [item["id"] for item in rows] == [challenge_id, challenge_id]
    assert rows[0]["entry_id"] == entry_id
    assert rows[0]["closes_at"] is not None
    assert rows[1]["entry_id"] != entry_id
    assert rows[1]["opens_at"] is None
    assert rows[1]["closes_at"] is None
    assert ChallengeAttempt.objects.filter(challenge_id=challenge_id).count() == before

    def states(client: APIClient) -> list[str]:
        listed = client.get("/api/v1/learning/paths/").json()["results"]
        path = next(item for item in listed if item["id"] == path_id)
        return [item["state"] for item in path["challenges"]]

    assert states(pending) == ["closed", "available"]
    assert states(done) == ["completed", "completed"]

    started = pending.post(
        f"/api/v1/learning/challenges/{challenge_id}/attempts/",
        {"path_id": path_id},
        format="json",
    )
    assert started.status_code == 200, started.content
    assert started.json()["attempt"]["status"] == "open"
    assert ChallengeAttempt.objects.filter(user_id=pending_id, challenge_id=challenge_id).count() == 2

    replay = done.post(
        f"/api/v1/learning/challenges/{challenge_id}/attempts/",
        {"path_id": path_id},
        format="json",
    )
    assert replay.status_code == 200, replay.content
    assert replay.json()["attempt"]["status"] == ChallengeAttempt.COMPLETED
    assert (
        ChallengeAttempt.objects.filter(
            user_id=done_id,
            challenge_id=challenge_id,
            status=ChallengeAttempt.COMPLETED,
        ).count()
        == 1
    )

    later = timezone.now() + timedelta(days=1)
    patched = teacher.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{challenge_id}/",
        {"entry_id": rows[1]["entry_id"], "closes_at": later.isoformat()},
        format="json",
    )
    assert patched.status_code == 200, patched.content
    fresh = patched.json()["challenges"]
    assert fresh[0]["closes_at"] == rows[0]["closes_at"]
    assert fresh[1]["closes_at"] != fresh[0]["closes_at"]
