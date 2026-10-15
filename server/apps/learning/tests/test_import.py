"""Abrir un archivo arma el lienzo y no toca el editor."""

from apps.tests.helpers import register

SOURCE = """
Algoritmo Laboratorio
    Definir n Como Entero;
    Leer n;
    Escribir n;
FinAlgoritmo
"""


def test_import_requires_a_session(client) -> None:
    response = client.post("/api/v1/learning/import/", {"source": SOURCE}, format="json")
    assert response.status_code == 403


def test_import_builds_the_canvas(client) -> None:
    register(client, email="lab-import@ejemplo.test", display_name="Alumno Lab")
    response = client.post("/api/v1/learning/import/", {"source": SOURCE}, format="json")
    assert response.status_code == 200
    body = response.json()
    block = body["workspace"]["blocks"]["blocks"][0]
    assert block["type"] == "traza_definir"
    assert block["fields"]["NOMBRE"] == "n"
    assert body["diagnostics"] == []


def test_import_builds_a_function(client) -> None:
    register(client, email="lab-import-fn@ejemplo.test")
    source = "Algoritmo Laboratorio\nFinAlgoritmo\nFuncion r <- F()\nFinFuncion\n"
    response = client.post("/api/v1/learning/import/", {"source": source}, format="json")
    assert response.status_code == 200
    body = response.json()
    kinds = [block["type"] for block in body["workspace"]["blocks"]["blocks"]]
    assert "traza_funcion" in kinds


def test_import_rejects_a_missing_text(client) -> None:
    register(client, email="lab-import-empty@ejemplo.test")
    response = client.post("/api/v1/learning/import/", {}, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["message"] == "El archivo debe ser texto."
