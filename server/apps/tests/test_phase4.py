"""Depurador: órdenes, puntos de interrupción y SSE en el proceso de desarrollo."""

from rest_framework.test import APIClient

from apps.executions.models import ExecutionEvent
from apps.tests.helpers import register

SOURCE = """Algoritmo Demo
    Definir n Como Entero;
    n <- 1;
    n <- 2;
    Escribir n;
FinAlgoritmo
"""

READ = """Algoritmo Lee
    Definir n Como Entero;
    Leer n;
    Escribir n;
FinAlgoritmo
"""


def _algorithm(client, source, name):
    project_id = client.get("/api/v1/projects/").json()["results"][0]["id"]
    created = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": name, "source": source},
        format="json",
    )
    assert created.status_code == 201, created.content
    return created.json()["id"]


def test_debug_steps_breakpoint_and_sse(client):
    register(client, email="depurar@ejemplo.test")
    algorithm_id = _algorithm(client, SOURCE, "Paso a paso")
    started = client.post(
        f"/api/v1/algorithms/{algorithm_id}/debug/",
        {"breakpoints": [4]},
        format="json",
    )
    assert started.status_code == 201, started.content
    body = started.json()
    assert body["status"] == "paused"
    assert body["debug"] is True
    assert body["line"] == 2
    assert body["call_stack"][0]["name"] == "Demo"

    stepped = client.post(
        f"/api/v1/executions/{body['id']}/control/",
        {"action": "step"},
        format="json",
    )
    assert stepped.status_code == 200, stepped.content
    assert stepped.json()["line"] == 3

    continued = client.post(
        f"/api/v1/executions/{body['id']}/control/",
        {"action": "continue"},
        format="json",
    )
    assert continued.json()["status"] == "paused"
    assert continued.json()["line"] == 4
    assert continued.json()["variables"]["n"] == "1"
    assert ExecutionEvent.objects.filter(execution_id=body["id"], kind="line").count() == 0

    events = client.get(f"/api/v1/executions/{body['id']}/events/?once=1")
    assert events.status_code == 200, events.content
    text = b"".join(events.streaming_content).decode()
    assert "event: paused" in text
    assert f'"execution_id": "{body["id"]}"' in text

    stopped = client.post(
        f"/api/v1/executions/{body['id']}/control/",
        {"action": "stop"},
        format="json",
    )
    assert stopped.json()["status"] == "cancelled"
    again = client.post(
        f"/api/v1/executions/{body['id']}/control/",
        {"action": "step"},
        format="json",
    )
    assert again.status_code == 409


def test_debug_input_restart_and_private_execution(client):
    register(client, email="depurar-io@ejemplo.test")
    algorithm_id = _algorithm(client, READ, "Lectura depurada")
    started = client.post(
        f"/api/v1/algorithms/{algorithm_id}/debug/",
        {"breakpoints": [1]},
        format="json",
    )
    execution_id = started.json()["id"]
    assert any(item["code"] == "W0504" for item in started.json()["diagnostics"])
    waiting = client.post(
        f"/api/v1/executions/{execution_id}/control/",
        {"action": "continue"},
        format="json",
    )
    assert waiting.json()["status"] == "waiting_input"
    sent = client.post(
        f"/api/v1/executions/{execution_id}/input/",
        {"text": "6"},
        format="json",
    )
    assert sent.status_code == 200, sent.content
    assert sent.json()["status"] == "completed"
    assert sent.json()["output"] == "6\n6\n"

    restarted = client.post(
        f"/api/v1/executions/{execution_id}/control/",
        {"action": "restart"},
        format="json",
    )
    assert restarted.status_code == 200, restarted.content
    assert restarted.json()["status"] == "paused"
    assert restarted.json()["line"] == 2

    stranger = APIClient()
    register(stranger, email="otro-depurar@ejemplo.test")
    hidden = stranger.get(f"/api/v1/executions/{execution_id}/events/?once=1")
    assert hidden.status_code == 404
