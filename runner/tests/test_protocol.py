"""El canal hacia el navegador no reenvía la consola acumulada."""

import json

from runner.protocol import sse_frame


def test_sse_frame_sends_the_new_text_only() -> None:
    frame = sse_frame(
        {
            "id": 4,
            "event": "output",
            "output": "Hola\n" * 1000,
            "text": "Hola\n",
            "status": "running",
        },
        "ejec-1",
    )
    assert frame.startswith("id: 4\nevent: output\n")
    data = json.loads(frame.split("data: ", 1)[1])
    assert "output" not in data
    assert data["text"] == "Hola\n"
    assert data["execution_id"] == "ejec-1"
