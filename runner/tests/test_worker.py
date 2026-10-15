"""El runner publica eventos sin importar Django."""

from __future__ import annotations

import json
import threading

import fakeredis

from runner.worker import run_worker

SOURCE = """Algoritmo Demo
    Definir n Como Entero;
    n <- 4;
    Escribir n;
FinAlgoritmo
"""


def test_worker_runs_a_program_and_publishes_output() -> None:
    client = fakeredis.FakeRedis(decode_responses=True)
    stop = threading.Event()
    thread = threading.Thread(target=run_worker, args=(client, stop), daemon=True)
    thread.start()
    try:
        client.rpush(
            "traza:jobs",
            json.dumps(
                {
                    "id": "ejec-1",
                    "source": SOURCE,
                    "profile": {"profile_key": "strict"},
                    "breakpoints": [],
                    "reply": "alta",
                    "interactive": False,
                }
            ),
        )
        started = client.blpop(["traza:reply:alta"], timeout=5)
        assert started is not None
        state = json.loads(started[1])["state"]
        assert state["status"] == "paused"
        client.rpush(
            "traza:cmd:ejec-1",
            json.dumps({"op": "continue", "reply": "sigue"}),
        )
        done = client.blpop(["traza:reply:sigue"], timeout=5)
        assert done is not None
        finished = json.loads(done[1])["state"]
        assert finished["status"] == "completed"
        assert finished["output"] == "4\n"
        assert client.get("traza:hb")
        stored = [json.loads(item) for item in client.lrange("traza:events:ejec-1", 0, -1)]
        events = [item["event"] for item in stored]
        assert "finished" in events
        assert all("output" not in item for item in stored)
        assert any(item.get("text") == "4\n" for item in stored)
    finally:
        stop.set()
        thread.join(timeout=3)
