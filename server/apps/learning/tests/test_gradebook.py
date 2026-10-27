"""La libreta de una ruta es un CSV con una fila por alumno."""

import csv
import io
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.learning.models import Challenge, ChallengeAttempt, PathEntry
from apps.tests.helpers import register

pytestmark = pytest.mark.django_db


def _teacher(email: str, name: str) -> APIClient:
    client = APIClient()
    register(client, email=email, display_name=name, role="teacher")
    return client


def test_la_libreta_tiene_una_fila_por_alumno_y_la_nota_del_intento():
    teacher = _teacher("libreta-profe@ejemplo.test", "Profe Libreta")
    other = _teacher("libreta-otra@ejemplo.test", "Otra Libreta")
    student = APIClient()
    created = register(student, email="libreta-ana@ejemplo.test", display_name="Ana Libreta")
    quiet = APIClient()
    second = register(quiet, email="libreta-beto@ejemplo.test", display_name="Beto Libreta")
    outsider = APIClient()
    outside = register(outsider, email="libreta-fuera@ejemplo.test", display_name="Fuera Libreta")
    colleague = _teacher("libreta-colega@ejemplo.test", "Colega Libreta")
    student_id = created.json()["id"]
    second_id = second.json()["id"]
    colleague_id = colleague.get("/api/v1/auth/me/").json()["id"]

    denied = student.get("/api/v1/learning/roster/00000000-0000-0000-0000-000000000000/progress/")
    assert denied.status_code == 403

    challenges = list(
        Challenge.objects.filter(is_published=True, unit__path__owner__isnull=True).order_by(
            "unit__position", "position"
        )[:2]
    )
    assert len(challenges) == 2
    first, second_challenge = challenges[1], challenges[0]
    created_path = teacher.post(
        "/api/v1/learning/authored/",
        {"name": "Libreta de lógica", "description": "Dos problemas"},
        format="json",
    )
    assert created_path.status_code == 201, created_path.content
    path_id = created_path.json()["id"]
    placed = teacher.put(
        f"/api/v1/learning/authored/{path_id}/challenges/",
        {"challenge_ids": [str(first.id), str(second_challenge.id)]},
        format="json",
    )
    assert placed.status_code == 200, placed.content

    group = teacher.post("/api/v1/communities/", {"name": "Grupo Libreta"}, format="json")
    assert group.status_code == 201, group.content
    community_id = group.json()["id"]
    for user_id in (student_id, second_id, colleague_id):
        added = teacher.post(
            f"/api/v1/communities/{community_id}/members/",
            {"user_id": user_id},
            format="json",
        )
        assert added.status_code == 201, added.content
    assigned = teacher.put(
        f"/api/v1/learning/authored/{path_id}/assignments/",
        {"community_ids": [community_id], "student_ids": []},
        format="json",
    )
    assert assigned.status_code == 200, assigned.content

    opens = timezone.now() - timedelta(days=2)
    closes = timezone.now() + timedelta(days=5)
    window = teacher.patch(
        f"/api/v1/learning/authored/{path_id}/challenges/{first.id}/",
        {"opens_at": opens.isoformat(), "closes_at": closes.isoformat()},
        format="json",
    )
    assert window.status_code == 200, window.content
    hidden = PathEntry.objects.get(path_id=path_id, challenge=second_challenge)
    hidden.withdrawn = True
    hidden.save(update_fields=["withdrawn"])

    user = get_user_model().objects.get(pk=student_id)
    ChallengeAttempt.objects.create(
        user=user,
        challenge=first,
        status=ChallengeAttempt.COMPLETED,
        score=80,
        summary="Puntuación 80.",
        finished_at=timezone.now(),
    )
    older = timezone.now() - timedelta(days=1)
    ChallengeAttempt.objects.create(
        user=user,
        challenge=first,
        status=ChallengeAttempt.COMPLETED,
        score=10,
        summary="Puntuación 10.",
        finished_at=older,
    )

    assert other.get(f"/api/v1/learning/roster/{path_id}/progress/").status_code == 404
    assert teacher.get(f"/api/v1/learning/roster/{outside.json()['id']}/").status_code == 404

    downloaded = teacher.get(f"/api/v1/learning/roster/{path_id}/progress/")
    assert downloaded.status_code == 200, downloaded.content
    assert downloaded["Content-Type"].startswith("text/csv")
    assert (
        downloaded["Content-Disposition"] == 'attachment; filename="progreso-libreta-de-logica.csv"'
    )
    text = downloaded.content.decode("utf-8")
    assert text.startswith("\ufeff")
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    start = timezone.localtime(opens).strftime("%Y-%m-%d")
    end = timezone.localtime(closes).strftime("%Y-%m-%d")
    assert rows[0] == [
        "Nombre",
        "Correo",
        "Comunidades",
        "Nota",
        f"{first.title} · {start} – {end} · 100",
    ]
    assert rows[1] == ["Ana Libreta", "libreta-ana@ejemplo.test", "Grupo Libreta", "80", "80"]
    assert rows[2] == ["Beto Libreta", "libreta-beto@ejemplo.test", "Grupo Libreta", "0", ""]
    assert all(row[0] != "Colega Libreta" for row in rows)
    assert all(row[0] != "Fuera Libreta" for row in rows)

    english = teacher.get(f"/api/v1/learning/roster/{path_id}/progress/?lang=en")
    english_rows = list(csv.reader(io.StringIO(english.content.decode("utf-8").lstrip("\ufeff"))))
    assert english_rows[0][:4] == ["Name", "Email", "Communities", "Grade"]

    solved = ChallengeAttempt.objects.create(
        user=get_user_model().objects.get(pk=second_id),
        challenge=second_challenge,
        status=ChallengeAttempt.COMPLETED,
        score=50,
        summary="Puntuación 50.",
        finished_at=timezone.now(),
    )
    assert solved.pk
    kept = teacher.get(f"/api/v1/learning/roster/{path_id}/progress/")
    kept_rows = list(csv.reader(io.StringIO(kept.content.decode("utf-8").lstrip("\ufeff"))))
    assert kept_rows[0][5] == f"{second_challenge.title} · 100"
    assert kept_rows[1] == [
        "Ana Libreta",
        "libreta-ana@ejemplo.test",
        "Grupo Libreta",
        "40",
        "80",
        "",
    ]
    assert kept_rows[2] == [
        "Beto Libreta",
        "libreta-beto@ejemplo.test",
        "Grupo Libreta",
        "25",
        "",
        "50",
    ]


def test_la_libreta_de_una_comunidad_no_mezcla_alumnos():
    teacher = _teacher("comunidad-profe@ejemplo.test", "Profe Comunidad")
    ana = APIClient()
    created = register(ana, email="comunidad-ana@ejemplo.test", display_name="Ana Comunidad")
    beto = APIClient()
    other = register(beto, email="comunidad-beto@ejemplo.test", display_name="Beto Comunidad")
    ana_id = created.json()["id"]
    beto_id = other.json()["id"]
    group_a = teacher.post("/api/v1/communities/", {"name": "Grupo Alfa"}, format="json")
    group_b = teacher.post("/api/v1/communities/", {"name": "Grupo Beta"}, format="json")
    assert group_a.status_code == 201, group_a.content
    assert group_b.status_code == 201, group_b.content
    added_a = teacher.post(
        f"/api/v1/communities/{group_a.json()['id']}/members/",
        {"user_id": ana_id},
        format="json",
    )
    added_b = teacher.post(
        f"/api/v1/communities/{group_b.json()['id']}/members/",
        {"user_id": beto_id},
        format="json",
    )
    assert added_a.status_code == 201, added_a.content
    assert added_b.status_code == 201, added_b.content

    roster = teacher.get("/api/v1/learning/roster/")
    assert roster.status_code == 200, roster.content
    path_id = next(item["id"] for item in roster.json()["routes"] if item["name"] == "Fundamentos")
    limited = teacher.get(f"/api/v1/learning/roster/{path_id}/progress/?community=Grupo Alfa")
    assert limited.status_code == 200, limited.content
    rows = list(csv.reader(io.StringIO(limited.content.decode("utf-8").lstrip("\ufeff"))))
    assert [row[0] for row in rows[1:]] == ["Ana Comunidad"]
    assert rows[1][2] == "Grupo Alfa"
    missing = teacher.get(f"/api/v1/learning/roster/{path_id}/progress/?community=No existe")
    assert missing.status_code == 404
