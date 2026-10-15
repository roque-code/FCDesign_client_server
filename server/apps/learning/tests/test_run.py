"""La pasada del laboratorio usa el depurador y no guarda una ejecución."""

import json

from apps.executions.models import Execution
from apps.learning.live import peek_run
from apps.learning.models import ChallengeAttempt, WorkspaceSnapshot
from apps.tests.helpers import register

SOURCE = """Algoritmo Demo
    Definir n Como Entero;
    n <- 1;
    Escribir n;
FinAlgoritmo
"""


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


def _read_workspace() -> dict[str, object]:
    return {
        "blocks": {
            "blocks": [
                {
                    "type": "traza_definir",
                    "id": "d1",
                    "fields": {"NOMBRE": "n", "TIPO": "entero"},
                    "next": {
                        "block": {
                            "type": "traza_leer",
                            "id": "r1",
                            "fields": {"NOMBRE": "n"},
                            "next": {
                                "block": {
                                    "type": "traza_escribir",
                                    "id": "e1",
                                    "inputs": {
                                        "VALOR": {
                                            "block": {
                                                "type": "traza_variable",
                                                "id": "v1",
                                                "fields": {"NOMBRE": "n", "TIPO": "entero"},
                                            }
                                        }
                                    },
                                }
                            },
                        }
                    },
                }
            ]
        }
    }


def _payloads(text: str) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for chunk in text.split("\n\n"):
        for line in chunk.splitlines():
            if line.startswith("data: "):
                body = json.loads(line[6:])
                if isinstance(body, dict):
                    found.append(body)
    return found


def test_run_steps_and_matches_editor_event_shape(client) -> None:
    register(client, email="lab-fase4@ejemplo.test")
    before_executions = Execution.objects.count()
    before_attempts = ChallengeAttempt.objects.count()
    before_snapshots = WorkspaceSnapshot.objects.count()
    started = client.post("/api/v1/learning/run/", {"workspace": _workspace()}, format="json")
    assert started.status_code == 200, started.content
    body = started.json()
    assert body["status"] == "paused"
    assert body["line"] == 2
    assign = next(item for item in body["bindings"] if item["block_id"] == "a1")
    stepped = client.post(
        f"/api/v1/learning/runs/{body['id']}/control/",
        {"action": "step"},
        format="json",
    )
    assert stepped.status_code == 200, stepped.content
    assert stepped.json()["line"] == assign["line"]
    assert stepped.json()["line"] == 3

    events = client.get(f"/api/v1/learning/runs/{body['id']}/events/?once=1")
    assert events.status_code == 200
    text = b"".join(events.streaming_content).decode()
    assert "event: paused" in text
    assert "event: expression_evaluated" not in text
    assert "event: variable_changed" not in text
    assert "event: condition_evaluated" not in text
    lab_keys = set(_payloads(text)[0])

    project_id = client.get("/api/v1/projects/").json()["results"][0]["id"]
    created = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Forma", "source": SOURCE},
        format="json",
    )
    debug = client.post(
        f"/api/v1/algorithms/{created.json()['id']}/debug/",
        {"breakpoints": []},
        format="json",
    )
    editor = client.get(f"/api/v1/executions/{debug.json()['id']}/events/?once=1")
    editor_text = b"".join(editor.streaming_content).decode()
    assert set(_payloads(editor_text)[0]) == lab_keys

    finished = client.post(
        f"/api/v1/learning/runs/{body['id']}/control/",
        {"action": "continue"},
        format="json",
    )
    assert finished.json()["status"] == "completed"
    assert finished.json()["output"] == "10\n"
    assert Execution.objects.count() == before_executions + 1
    assert ChallengeAttempt.objects.count() == before_attempts
    assert WorkspaceSnapshot.objects.count() == before_snapshots


def test_run_reads_rejects_and_restarts(client) -> None:
    register(client, email="lab-fase4-leer@ejemplo.test")
    started = client.post("/api/v1/learning/run/", {"workspace": _read_workspace()}, format="json")
    run_id = started.json()["id"]
    waiting = client.post(
        f"/api/v1/learning/runs/{run_id}/control/",
        {"action": "continue"},
        format="json",
    )
    assert waiting.json()["status"] == "waiting_input"
    assert waiting.json()["pending_input"]["name"] == "n"
    rejected = client.post(
        f"/api/v1/learning/runs/{run_id}/input/",
        {"text": "no"},
        format="json",
    )
    assert rejected.json()["status"] == "waiting_input"
    assert rejected.json()["output"] == ""
    assert any(item["code"] == "E0406" for item in rejected.json()["diagnostics"])
    stream = client.get(f"/api/v1/learning/runs/{run_id}/events/?once=1")
    assert "event: input_rejected" in b"".join(stream.streaming_content).decode()
    accepted = client.post(
        f"/api/v1/learning/runs/{run_id}/input/",
        {"text": "4"},
        format="json",
    )
    assert accepted.json()["status"] == "completed"
    assert accepted.json()["output"] == "4\n4\n"

    restarted = client.post(
        f"/api/v1/learning/runs/{run_id}/control/",
        {"action": "restart"},
        format="json",
    )
    assert restarted.json()["status"] == "paused"
    assert restarted.json()["line"] == 2
    assert restarted.json()["output"] == ""


def test_run_stops_and_drops_the_previous_pass(client) -> None:
    register(client, email="lab-fase4-stop@ejemplo.test")
    first = client.post("/api/v1/learning/run/", {"workspace": _workspace()}, format="json").json()
    paused = client.post(
        f"/api/v1/learning/runs/{first['id']}/control/",
        {"action": "pause"},
        format="json",
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"
    invalid = client.post(
        f"/api/v1/learning/runs/{first['id']}/control/",
        {"action": "brincar"},
        format="json",
    )
    assert invalid.status_code == 400
    not_text = client.post(
        f"/api/v1/learning/runs/{first['id']}/input/",
        {"text": 4},
        format="json",
    )
    assert not_text.status_code == 400
    early = client.post(
        f"/api/v1/learning/runs/{first['id']}/input/",
        {"text": "4"},
        format="json",
    )
    assert early.status_code == 409
    huge = client.post(
        f"/api/v1/learning/runs/{first['id']}/input/",
        {"text": "x" * 100_001},
        format="json",
    )
    assert huge.status_code == 400
    stopped = client.post(
        f"/api/v1/learning/runs/{first['id']}/control/",
        {"action": "stop"},
        format="json",
    )
    assert stopped.json()["status"] == "cancelled"
    again = client.post(
        f"/api/v1/learning/runs/{first['id']}/control/",
        {"action": "step"},
        format="json",
    )
    assert again.status_code == 409
    second = client.post("/api/v1/learning/run/", {"workspace": _workspace()}, format="json")
    assert second.status_code == 200
    gone = client.get(f"/api/v1/learning/runs/{first['id']}/events/?once=1")
    assert gone.status_code == 404


def test_run_does_not_start_with_errors(client) -> None:
    register(client, email="lab-fase4-error@ejemplo.test")
    unknown = client.post(
        "/api/v1/learning/run/",
        {"workspace": {"blocks": {"blocks": [{"type": "traza_desconocido", "id": "x"}]}}},
        format="json",
    )
    assert unknown.status_code == 200
    assert unknown.json()["id"] is None
    assert unknown.json()["status"] == "error"
    assert unknown.json()["diagnostics"][0]["code"] == "L0001"

    semantic = client.post(
        "/api/v1/learning/run/",
        {
            "workspace": {
                "blocks": {
                    "blocks": [
                        {
                            "type": "traza_asignar",
                            "id": "a1",
                            "fields": {"NOMBRE": "precio"},
                            "inputs": {
                                "VALOR": {
                                    "block": {
                                        "type": "traza_entero",
                                        "id": "n1",
                                        "fields": {"VALOR": 1},
                                    }
                                }
                            },
                        }
                    ]
                }
            }
        },
        format="json",
    )
    assert semantic.json()["id"] is None
    assert any(item["code"] == "E0301" for item in semantic.json()["diagnostics"])
    assert Execution.objects.count() == 0


def test_warning_still_runs(client) -> None:
    register(client, email="lab-fase4-aviso@ejemplo.test")
    started = client.post(
        "/api/v1/learning/run/",
        {
            "workspace": {
                "blocks": {
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
                                }
                            },
                        }
                    ]
                }
            }
        },
        format="json",
    )
    body = started.json()
    assert body["id"]
    assert body["status"] == "paused"
    assert any(item["code"] == "W0503" for item in body["diagnostics"])


def test_run_publishes_each_console_frame(client, monkeypatch) -> None:
    monkeypatch.setattr("language_core.debugger.pause_for", lambda *_args, **_kwargs: None)
    register(client, email="lab-animacion@ejemplo.test")

    def text(block_id: str, value: str) -> dict[str, object]:
        return {
            "type": "traza_escribir",
            "id": block_id,
            "inputs": {
                "VALOR": {
                    "block": {
                        "type": "traza_cadena",
                        "id": f"{block_id}-texto",
                        "fields": {"VALOR": value},
                    }
                }
            },
        }

    esperar = {
        "type": "traza_esperar",
        "id": "w1",
        "inputs": {
            "SEGUNDOS": {"block": {"type": "traza_entero", "id": "n1", "fields": {"VALOR": 1}}}
        },
    }
    chain: dict[str, object] = esperar
    for block in (
        text("e2", "Listo"),
        {"type": "traza_borrar_pantalla", "id": "b1"},
        text("e1", "Hola"),
    ):
        chain = {**block, "next": {"block": chain}}
    started = client.post(
        "/api/v1/learning/run/",
        {"workspace": {"blocks": {"blocks": [chain]}}},
        format="json",
    )
    assert started.status_code == 200, started.content
    assert started.json()["status"] == "paused"
    finished = client.post(
        f"/api/v1/learning/runs/{started.json()['id']}/control/",
        {"action": "continue"},
        format="json",
    )
    assert finished.json()["status"] == "completed"
    assert finished.json()["output"] == "Listo\n"
    live = peek_run(started.json()["id"])
    assert live is not None
    frames = [event.get("output") for event in live.events if event.get("event") == "output"]
    assert frames == ["Hola\n", "", "Listo\n"]


def test_run_requires_a_session_and_hides_other_users(client) -> None:
    from rest_framework.test import APIClient

    anonymous = client.post("/api/v1/learning/run/", {"workspace": {}}, format="json")
    assert anonymous.status_code == 403
    register(client, email="lab-fase4-dueno@ejemplo.test")
    started = client.post("/api/v1/learning/run/", {"workspace": {}}, format="json")
    assert started.json()["status"] == "completed"
    stranger = APIClient()
    register(stranger, email="lab-fase4-otro@ejemplo.test")
    hidden = stranger.get(f"/api/v1/learning/runs/{started.json()['id']}/events/?once=1")
    assert hidden.status_code == 404
    missing = client.post("/api/v1/learning/run/", {}, format="json")
    assert missing.status_code == 400
