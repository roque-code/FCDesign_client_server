"""Abre un archivo de pseudocódigo y devuelve el lienzo."""

from typing import Any

from django.conf import settings

from apps.language.services import diagnostic_payload
from config.errors import DomainError
from language_core.block_import import workspace_from_source


def import_source(data: dict[str, Any]) -> dict[str, Any]:
    source = data.get("source")
    if not isinstance(source, str):
        raise DomainError("El archivo debe ser texto.")
    if len(source.encode("utf-8")) > settings.MAX_SOURCE_BYTES:
        raise DomainError("El archivo supera 64 KiB.")
    imported = workspace_from_source(source)
    return {
        "workspace": imported.workspace,
        "diagnostics": [diagnostic_payload(item) for item in imported.diagnostics],
    }
