"""El enunciado puede guardar una imagen y volver a mostrarla."""

import base64

import pytest
from rest_framework.test import APIClient

from apps.learning.models import ChallengeFigure
from apps.tests.helpers import register

pytestmark = pytest.mark.django_db

_JPEG = b"\xff\xd8\xff" + b"\x00" * 40


def _photo() -> str:
    return f"data:image/jpeg;base64,{base64.b64encode(_JPEG).decode('ascii')}"


def _classify(title: str, prompt: str) -> dict:
    return {
        "title": title,
        "prompt": prompt,
        "activity_type": "classify",
        "concept": "io",
        "difficulty": 1,
        "points": 10,
        "categories": ["entrada", "salida"],
        "items": [
            {"text": "Leer el nombre", "category": "entrada"},
            {"text": "Mostrar el nombre", "category": "salida"},
        ],
    }


def test_el_docente_sube_una_imagen_y_el_alumno_la_ve_en_el_enunciado():
    teacher = APIClient()
    register(teacher, email="figura-profe@ejemplo.test", display_name="Profe Figura", role="teacher")
    student = APIClient()
    register(student, email="figura-alumno@ejemplo.test", display_name="Alumno Figura")
    outsider = APIClient()
    register(outsider, email="figura-otro@ejemplo.test", display_name="Otro Figura", role="teacher")

    uploaded = teacher.post("/api/v1/learning/figures/", {"image": _photo()}, format="json")
    assert uploaded.status_code == 201, uploaded.content
    url = uploaded.json()["url"]
    figure = ChallengeFigure.objects.get()
    assert figure.challenge_id is None
    assert teacher.get(url).content == _JPEG
    assert student.get(url).status_code == 404
    assert outsider.get(url).status_code == 404

    created = teacher.post(
        "/api/v1/learning/authored/challenges/",
        _classify("Con figura", f"Mira el dibujo.\n\n![figura]({url})"),
        format="json",
    )
    assert created.status_code == 201, created.content
    figure.refresh_from_db()
    assert figure.challenge_id is not None
    seen = student.get(url)
    assert seen.status_code == 200
    assert seen["Content-Type"] == "image/jpeg"
    assert seen.content == _JPEG


def test_rechaza_una_imagen_que_no_es_jpg_png_gif_o_webp():
    teacher = APIClient()
    register(teacher, email="figura-mala@ejemplo.test", display_name="Profe Mala", role="teacher")
    svg = "data:image/svg+xml;base64," + base64.b64encode(b"<svg xmlns='http://www.w3.org/2000/svg'/>" * 2).decode()
    refused = teacher.post("/api/v1/learning/figures/", {"image": svg}, format="json")
    assert refused.status_code == 400
    assert ChallengeFigure.objects.count() == 0
