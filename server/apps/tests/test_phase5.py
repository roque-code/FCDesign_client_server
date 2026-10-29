"""Consulta del diagrama y caché invalidable."""

from apps.projects.models import Algorithm
from apps.tests.helpers import PASSWORD, refresh_csrf, register

SOURCE = """
Algoritmo Demo
    Definir a Como Entero;
    a <- 1;
    Si a == 1 Entonces
        Escribir a;
    FinSi
FinAlgoritmo
"""


def _create(client) -> str:
    register(client, email="fase5@ejemplo.test")
    project = client.post("/api/v1/projects/", {"name": "Diagramas"}, format="json").json()["id"]
    created = client.post(
        "/api/v1/algorithms/",
        {"project_id": project, "name": "Demo", "source": SOURCE},
        format="json",
    )
    assert created.status_code == 201, created.content
    return created.json()["id"]


def test_flowchart_returns_the_graph_and_caches_it(client):
    algorithm_id = _create(client)
    first = client.get(f"/api/v1/algorithms/{algorithm_id}/flowchart/")
    assert first.status_code == 200, first.content
    body = first.json()
    kinds = [node["kind"] for node in body["graph"]["nodes"]]
    assert "decision" in kinds
    assert "join" in kinds
    decision = next(node for node in body["graph"]["nodes"] if node["kind"] == "decision")
    assert decision["text"] == "a == 1"
    assert decision["line"] == 5
    stored = Algorithm.objects.get(id=algorithm_id).flowchart
    assert stored["source_hash"]
    assert stored["graph"]["entry"] == body["graph"]["entry"]
    second = client.get(f"/api/v1/algorithms/{algorithm_id}/flowchart/")
    assert second.json()["graph"] == body["graph"]


def test_flowchart_rejects_another_user_and_a_broken_source(client):
    algorithm_id = _create(client)
    client.post("/api/v1/auth/logout/")
    refresh_csrf(client)
    register(client, email="otra@ejemplo.test")
    hidden = client.get(f"/api/v1/algorithms/{algorithm_id}/flowchart/")
    assert hidden.status_code == 404

    client.post("/api/v1/auth/logout/")
    refresh_csrf(client)
    logged = client.post(
        "/api/v1/auth/login/",
        {"email": "fase5@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert logged.status_code == 200
    refresh_csrf(client)
    broken = client.patch(
        f"/api/v1/algorithms/{algorithm_id}/",
        {"source": "Si\n"},
        format="json",
    )
    assert broken.status_code == 200
    response = client.get(f"/api/v1/algorithms/{algorithm_id}/flowchart/")
    assert response.status_code == 200
    assert response.json()["graph"] is None
    assert response.json()["diagnostics"]
    assert Algorithm.objects.get(id=algorithm_id).flowchart is None


def test_flowchart_cache_skips_a_second_compile(client, monkeypatch):
    algorithm_id = _create(client)
    assert client.get(f"/api/v1/algorithms/{algorithm_id}/flowchart/").status_code == 200

    def boom(*_args, **_kwargs):
        raise AssertionError("no había que compilar otra vez")

    monkeypatch.setattr("apps.flowcharts.services.compile_source", boom)
    second = client.get(f"/api/v1/algorithms/{algorithm_id}/flowchart/")
    assert second.status_code == 200
    assert second.json()["graph"]["nodes"]


def test_changing_the_source_rebuilds_the_graph(client):
    algorithm_id = _create(client)
    client.get(f"/api/v1/algorithms/{algorithm_id}/flowchart/")
    before = Algorithm.objects.get(id=algorithm_id).flowchart["source_hash"]
    patched = client.patch(
        f"/api/v1/algorithms/{algorithm_id}/",
        {"source": 'Algoritmo Demo\n    Escribir "hola";\nFinAlgoritmo\n'},
        format="json",
    )
    assert patched.status_code == 200
    assert Algorithm.objects.get(id=algorithm_id).flowchart is None
    response = client.get(f"/api/v1/algorithms/{algorithm_id}/flowchart/")
    texts = [node["text"] for node in response.json()["graph"]["nodes"]]
    assert 'Escribir "hola"' in texts
    assert Algorithm.objects.get(id=algorithm_id).flowchart["source_hash"] != before
