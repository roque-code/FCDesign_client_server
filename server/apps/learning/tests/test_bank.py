"""El banco compartido trae 200 retos que el laboratorio puede ejecutar."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.learning.bank_data import BANK_NAME, ROUTE_NAME, build_bank
from apps.learning.models import Challenge, ChallengeAttempt, PathEntry
from apps.tests.helpers import register

pytestmark = pytest.mark.django_db


def test_el_banco_tiene_doscientos_retos_de_los_cuatro_tipos():
    bank = build_bank()
    challenges = [item for unit in bank["units"] for item in unit["challenges"]]
    assert len(challenges) == 200
    assert {item["activity_type"] for item in challenges} == {
        "classify",
        "order",
        "build",
        "predict",
    }
    assert {item["difficulty"] for item in challenges} == {1, 2, 3, 4, 5}
    for item in challenges:
        kinds = {hint["level"] for hint in item["hints"]}
        assert 5 in kinds
        assert any("Esta es la solución explicada" in hint["body"] for hint in item["hints"])
        if item["activity_type"] == "order":
            shown = [row["id"] for row in item["restrictions"]["items"]]
            assert item["restrictions"]["solution"] != shown
        if item["activity_type"] == "build":
            assert "source" not in item["restrictions"]
            assert item["cases"][0]["expected_output"].endswith("\n")
        if item["activity_type"] == "predict":
            assert item["restrictions"]["accepted"]
            assert item["restrictions"]["starter"]["blocks"]["blocks"]


def test_el_banco_queda_publicado_y_fuera_de_la_ruta_del_alumno():
    stored = Challenge.objects.filter(unit__path__name=BANK_NAME, is_published=True)
    assert stored.count() == 200
    path = stored.first().unit.path
    assert path.is_bank is True
    assert path.owner_id is None
    assert path.is_published is True
    route_ids = list(
        PathEntry.objects.filter(path__name=ROUTE_NAME)
        .order_by("position")
        .values_list("challenge_id", flat=True)
    )
    ordered = list(
        stored.order_by("unit__position", "position").values_list("id", flat=True)
    )
    assert route_ids == ordered
    route = PathEntry.objects.filter(path__name=ROUTE_NAME).first().path
    assert route.is_bank is False
    assert route.is_published is True
    assert route.owner_id is None


def test_el_docente_ve_el_banco_completo_y_el_alumno_no():
    student = APIClient()
    register(student, email="banco-alumno@ejemplo.test", display_name="Alumno Banco")
    assert student.get("/api/v1/learning/bank/").status_code == 403

    teacher = APIClient()
    register(teacher, email="banco-profe@ejemplo.test", display_name="Profe Banco", role="teacher")
    response = teacher.get("/api/v1/learning/bank/")
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["name"] == BANK_NAME
    challenges = [item for unit in body["units"] for item in unit["challenges"]]
    assert len(challenges) == 200
    assert "starter" not in response.content.decode()
    first = challenges[0]
    assert first["title"] == "Nombre, tipo y valor"
    assert first["owned"] is False
    assert first["categories"]
    assert first["items"][0]["category"]
    assert first["prompt"]
    assert first["hints"]
    ordered = next(item for item in challenges if item["activity_type"] == "order")
    assert ordered["items"][0]["text"]
    predicted = next(item for item in challenges if item["activity_type"] == "predict")
    assert predicted["source"].startswith("Algoritmo")
    assert predicted["accepted"]
    built = next(item for item in challenges if item["activity_type"] == "build")
    assert built["expected_output"].endswith("\n")
    assert built["question"]


def _classify(title: str) -> dict:
    return {
        "title": title,
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
        "hints": ["Fíjate quién produce el dato."],
    }


def test_el_docente_crea_edita_y_da_de_baja_un_reto_del_banco():
    student = APIClient()
    register(student, email="banco-baja-alumno@ejemplo.test", display_name="Alumno Baja")
    teacher = APIClient()
    register(teacher, email="banco-baja-profe@ejemplo.test", display_name="Profe Baja", role="teacher")
    other = APIClient()
    register(other, email="banco-baja-otro@ejemplo.test", display_name="Otro Baja", role="teacher")

    created = teacher.post("/api/v1/learning/authored/challenges/", _classify("Señales propias"), format="json")
    assert created.status_code == 201, created.content
    own_id = created.json()["id"]
    cards = [
        item
        for unit in teacher.get("/api/v1/learning/bank/").json()["units"]
        for item in unit["challenges"]
    ]
    own = next(item for item in cards if item["id"] == own_id)
    assert own["owned"] is True
    assert len(cards) == 201
    others = [
        item
        for unit in other.get("/api/v1/learning/bank/").json()["units"]
        for item in unit["challenges"]
    ]
    assert all(item["id"] != own_id for item in others)
    assert other.delete(f"/api/v1/learning/authored/challenges/{own_id}/").status_code == 404
    assert student.delete(f"/api/v1/learning/authored/challenges/{own_id}/").status_code == 403

    shared = Challenge.objects.select_related("unit__path").get(
        title="Nombre, tipo y valor", unit__path__name=BANK_NAME
    )
    draft = teacher.get(f"/api/v1/learning/authored/challenges/{shared.id}/").json()
    edited = teacher.patch(
        f"/api/v1/learning/authored/challenges/{shared.id}/",
        {
            "title": draft["title"],
            "prompt": f"{draft['prompt']} Revisa el nombre.",
            "activity_type": draft["activity_type"],
            "concept": draft["concept"],
            "difficulty": draft["difficulty"],
            "points": draft["points"],
            "categories": draft["categories"],
            "items": draft["items"],
            "hints": draft["hints"],
        },
        format="json",
    )
    assert edited.status_code == 200, edited.content
    shared.refresh_from_db()
    assert shared.unit.path.name == BANK_NAME
    assert shared.prompt.endswith("Revisa el nombre.")
    ordered = Challenge.objects.filter(activity_type="order", unit__path__name=BANK_NAME).first()
    assert ordered is not None
    solution = ordered.restrictions["solution"]
    by_id = {item["id"]: item["text"] for item in ordered.restrictions["items"]}
    seen = teacher.get(f"/api/v1/learning/authored/challenges/{ordered.id}/").json()
    assert [item["text"] for item in seen["items"]] == [by_id[item_id] for item_id in solution]

    fundamentos = (
        Challenge.objects.filter(is_published=True, unit__path__owner__isnull=True)
        .exclude(unit__path__name=BANK_NAME)
        .first()
    )
    assert fundamentos is not None
    assert teacher.delete(f"/api/v1/learning/authored/challenges/{fundamentos.id}/").status_code == 404

    plain = Challenge.objects.filter(unit__path__name=BANK_NAME, title="Máximo de dos").get()
    assert teacher.delete(f"/api/v1/learning/authored/challenges/{plain.id}/").status_code == 204
    assert not Challenge.objects.filter(pk=plain.id).exists()
    assert not PathEntry.objects.filter(challenge_id=plain.id).exists()

    used = Challenge.objects.filter(unit__path__name=BANK_NAME, is_published=True).first()
    assert used is not None
    user = get_user_model().objects.get(email="banco-baja-profe@ejemplo.test")
    ChallengeAttempt.objects.create(challenge=used, user=user, status="completed", score=80)
    assert teacher.delete(f"/api/v1/learning/authored/challenges/{used.id}/").status_code == 204
    used.refresh_from_db()
    assert used.is_published is False
    assert not PathEntry.objects.filter(challenge=used).exists()
    assert ChallengeAttempt.objects.filter(challenge=used).count() == 1

    assert teacher.delete(f"/api/v1/learning/authored/challenges/{own_id}/").status_code == 204
    left = [
        item["id"]
        for unit in teacher.get("/api/v1/learning/bank/").json()["units"]
        for item in unit["challenges"]
    ]
    assert own_id not in left
    assert str(used.id) not in left
    assert str(plain.id) not in left
