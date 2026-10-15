"""Ejecución a través de Redis, con el mismo contrato que el proceso local."""

from __future__ import annotations

import threading

import fakeredis
import pytest
from django.test import override_settings

from apps.tests.helpers import register
from runner.worker import run_worker

SOURCE = """Algoritmo Demo
    Definir n Como Entero;
    n <- 4;
    Escribir n;
FinAlgoritmo
"""

READ = """Algoritmo Lee
    Definir n Como Entero;
    Leer n;
    Escribir n;
FinAlgoritmo
"""


@pytest.fixture
def redis_runner(monkeypatch):
    client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("apps.executions.bus.get_redis", lambda: client)
    stop = threading.Event()
    thread = threading.Thread(target=run_worker, args=(client, stop), daemon=True)
    thread.start()
    yield client
    stop.set()
    thread.join(timeout=3)


@override_settings(EXECUTION_RUNNER="redis")
def test_redis_runner_executes_reads_and_reports_health(client, redis_runner):
    register(client, email="fase6@ejemplo.test")
    redis_runner.set("traza:hb", "1", ex=30)
    ready = client.get("/api/health/")
    assert ready.status_code == 200
    assert ready.json()["checks"]["runner"] is True

    project_id = client.get("/api/v1/projects/").json()["results"][0]["id"]
    algorithm_id = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Demo redis", "source": SOURCE},
        format="json",
    ).json()["id"]
    paused = client.post(f"/api/v1/algorithms/{algorithm_id}/execute/")
    assert paused.status_code == 201, paused.content
    body = paused.json()
    assert body["status"] == "paused"
    assert body["debug"] is False
    continued = client.post(
        f"/api/v1/executions/{body['id']}/control/",
        {"action": "continue"},
        format="json",
    )
    assert continued.status_code == 200, continued.content
    assert continued.json()["status"] == "completed"
    assert continued.json()["output"] == "4\n"
    events = client.get(f"/api/v1/executions/{body['id']}/events/?once=1")
    assert events.status_code == 200
    text = b"".join(events.streaming_content).decode()
    assert "event: finished" in text

    reader_id = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Lee redis", "source": READ},
        format="json",
    ).json()["id"]
    reading = client.post(f"/api/v1/algorithms/{reader_id}/execute/")
    assert reading.status_code == 201, reading.content
    assert reading.json()["status"] == "paused"
    stepped = client.post(
        f"/api/v1/executions/{reading.json()['id']}/control/",
        {"action": "continue"},
        format="json",
    )
    assert stepped.status_code == 200, stepped.content
    assert stepped.json()["status"] == "waiting_input"
    accepted = client.post(
        f"/api/v1/executions/{reading.json()['id']}/input/",
        {"text": "7"},
        format="json",
    )
    assert accepted.status_code == 200, accepted.content
    assert accepted.json()["output"] == "7\n7\n"
    assert accepted.json()["status"] == "completed"


@override_settings(EXECUTION_RUNNER="redis")
def test_health_degrades_without_runner(client, monkeypatch):
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("apps.executions.bus.get_redis", lambda: fake)
    waiting = client.get("/api/health/")
    assert waiting.status_code == 503
    assert waiting.json()["checks"]["database"] is True
    assert waiting.json()["checks"]["runner"] is False


@override_settings(EXECUTION_RUNNER="redis")
def test_redis_runner_steps_a_lab_workspace(client, redis_runner):
    from apps.learning.tests.test_run import _workspace

    register(client, email="fase6-lab@ejemplo.test")
    started = client.post("/api/v1/learning/run/", {"workspace": _workspace()}, format="json")
    assert started.status_code == 200, started.content
    body = started.json()
    assert body["status"] == "paused"
    assert body["id"]
    stepped = client.post(
        f"/api/v1/learning/runs/{body['id']}/control/",
        {"action": "step"},
        format="json",
    )
    assert stepped.status_code == 200, stepped.content
    assert stepped.json()["status"] in ("paused", "completed")
    events = client.get(f"/api/v1/learning/runs/{body['id']}/events/?once=1")
    assert events.status_code == 200
    assert "event:" in b"".join(events.streaming_content).decode()
