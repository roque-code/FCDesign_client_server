"""La vista previa traduce el lienzo y no lo guarda."""

from apps.tests.helpers import register


def _workspace() -> dict[str, object]:
    return {
        "blocks": {
            "languageVersion": 0,
            "blocks": [
                {
                    "type": "traza_definir",
                    "id": "d1",
                    "fields": {"NOMBRE": "precio", "TIPO": "entero"},
                    "next": {
                        "block": {
                            "type": "traza_asignar",
                            "id": "a1",
                            "fields": {"NOMBRE": "precio"},
                            "inputs": {
                                "VALOR": {
                                    "block": {
                                        "type": "traza_entero",
                                        "id": "n1",
                                        "fields": {"VALOR": 10},
                                    }
                                }
                            },
                            "next": {
                                "block": {
                                    "type": "traza_escribir",
                                    "id": "e1",
                                    "inputs": {
                                        "VALOR": {
                                            "block": {
                                                "type": "traza_variable",
                                                "id": "v1",
                                                "fields": {"NOMBRE": "precio", "TIPO": "entero"},
                                            }
                                        }
                                    },
                                }
                            },
                        }
                    },
                }
            ],
        }
    }


def test_preview_requires_a_session(client) -> None:
    response = client.post(
        "/api/v1/learning/preview/",
        {"workspace": {"blocks": {"blocks": []}}},
        format="json",
    )
    assert response.status_code == 403


def test_preview_returns_pseudocode(client) -> None:
    register(client, email="lab-fase3@ejemplo.test", display_name="Alumno Lab")
    response = client.post(
        "/api/v1/learning/preview/",
        {"workspace": _workspace()},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert "Definir precio Como Entero;" in body["source"]
    assert "precio <- 10;" in body["source"]
    assert "Escribir precio;" in body["source"]
    assert body["diagnostics"] == []
    assert body["bindings"][0]["block_id"] == "d1"
    assert body["bindings"][0]["line"] == 2


def test_preview_reports_an_unknown_block(client) -> None:
    register(client, email="lab-fase3b@ejemplo.test")
    response = client.post(
        "/api/v1/learning/preview/",
        {"workspace": {"blocks": {"blocks": [{"type": "traza_desconocido", "id": "x"}]}}},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == ""
    assert body["diagnostics"][0]["code"] == "L0001"


def test_preview_rejects_a_missing_workspace(client) -> None:
    register(client, email="lab-fase3c@ejemplo.test")
    response = client.post("/api/v1/learning/preview/", {}, format="json")
    assert response.status_code == 400


def test_preview_rejects_a_huge_workspace(client) -> None:
    register(client, email="lab-fase3d@ejemplo.test")
    response = client.post(
        "/api/v1/learning/preview/",
        {"workspace": {"blocks": {"blocks": []}, "pad": "x" * 300_000}},
        format="json",
    )
    assert response.status_code == 400
