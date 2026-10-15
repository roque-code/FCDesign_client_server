"""Vista previa del lienzo. No guarda ni ejecuta."""

import json
from typing import Any

from apps.language.services import diagnostic_payload
from config.errors import DomainError
from language_core.block_adapter import adapt_workspace

MAX_WORKSPACE_BYTES = 256 * 1024


def load_workspace(data: dict[str, Any]) -> dict[str, Any]:
    workspace = data.get("workspace")
    if not isinstance(workspace, dict):
        raise DomainError("Falta el workspace.")
    size = len(json.dumps(workspace, ensure_ascii=False).encode())
    if size > MAX_WORKSPACE_BYTES:
        raise DomainError("El workspace es demasiado grande.")
    return workspace


def preview_workspace(data: dict[str, Any]) -> dict[str, object]:
    adapted = adapt_workspace(load_workspace(data))
    return {
        "source": adapted.source,
        "bindings": [
            {"block_id": item.block_id, "line": item.line, "column": item.column}
            for item in adapted.bindings
        ],
        "diagnostics": [diagnostic_payload(item) for item in adapted.diagnostics],
    }
