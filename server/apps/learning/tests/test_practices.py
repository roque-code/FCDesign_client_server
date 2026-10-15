"""Una práctica libre se guarda, se abre, se descarga por su fuente y se borra."""

from rest_framework.test import APIClient

from apps.learning.practices import MAX_PRACTICES
from apps.tests.helpers import register

WORKSPACE = {
    "blocks": {
        "languageVersion": 0,
        "blocks": [
            {
                "type": "traza_definir",
                "id": "d1",
                "fields": {"NOMBRE": "precio", "TIPO": "entero"},
            }
        ],
    }
}


def test_una_practica_se_guarda_se_abre_y_se_borra(client) -> None:
    register(client, email="lab-practica@ejemplo.test")
    created = client.post(
        "/api/v1/learning/practices/",
        {"name": "  Repaso  ", "workspace": WORKSPACE},
        format="json",
    )
    assert created.status_code == 201, created.content
    body = created.json()
    assert body["name"] == "Repaso"
    assert "Definir precio Como Entero;" in body["source"]
    assert body["workspace"]["blocks"]["blocks"][0]["id"] == "d1"
    practice_id = body["id"]

    listed = client.get("/api/v1/learning/practices/")
    assert listed.status_code == 200
    row = listed.json()["results"][0]
    assert row["id"] == practice_id
    assert "workspace" not in row
    assert "Definir precio Como Entero;" in row["source"]

    opened = client.get(f"/api/v1/learning/practices/{practice_id}/")
    assert opened.status_code == 200
    assert opened.json()["workspace"]["blocks"]["blocks"][0]["type"] == "traza_definir"

    renamed = client.patch(
        f"/api/v1/learning/practices/{practice_id}/",
        {"name": "Repaso 2", "workspace": {"blocks": {"languageVersion": 0, "blocks": []}}},
        format="json",
    )
    assert renamed.status_code == 200, renamed.content
    assert renamed.json()["name"] == "Repaso 2"
    assert "Algoritmo Laboratorio" in renamed.json()["source"]

    stranger = APIClient()
    register(stranger, email="lab-practica-ajena@ejemplo.test")
    hidden = stranger.get(f"/api/v1/learning/practices/{practice_id}/")
    assert hidden.status_code == 404
    denied = stranger.delete(f"/api/v1/learning/practices/{practice_id}/")
    assert denied.status_code == 404

    removed = client.delete(f"/api/v1/learning/practices/{practice_id}/")
    assert removed.status_code == 204
    gone = client.get(f"/api/v1/learning/practices/{practice_id}/")
    assert gone.status_code == 404


def test_el_nombre_vacio_y_el_duplicado_se_rechazan(client, monkeypatch) -> None:
    register(client, email="lab-practica-nombre@ejemplo.test")
    empty = client.post(
        "/api/v1/learning/practices/",
        {"name": "   ", "workspace": WORKSPACE},
        format="json",
    )
    assert empty.status_code == 400

    first = client.post(
        "/api/v1/learning/practices/",
        {"name": "Repaso", "workspace": WORKSPACE},
        format="json",
    )
    assert first.status_code == 201
    duplicate = client.post(
        "/api/v1/learning/practices/",
        {"name": "Repaso", "workspace": WORKSPACE},
        format="json",
    )
    assert duplicate.status_code == 409

    monkeypatch.setattr("apps.learning.practices.MAX_PRACTICES", 1)
    assert MAX_PRACTICES == 40
    capped = client.post(
        "/api/v1/learning/practices/",
        {"name": "Otra", "workspace": WORKSPACE},
        format="json",
    )
    assert capped.status_code == 409
