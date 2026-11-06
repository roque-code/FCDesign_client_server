"""Imágenes que acompañan el enunciado de un reto."""

from __future__ import annotations

import base64
import binascii
import re

from apps.learning.models import Challenge, ChallengeFigure
from config.errors import DomainError

_MAX_FIGURE = 1_200_000
_KINDS = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/webp": (b"RIFF",),
}
_FIGURE_IDS = re.compile(
    r"/api/v1/learning/figures/"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/",
    re.IGNORECASE,
)
_MISSING = "No se encontró la imagen."


def store_figure(teacher, value: object) -> dict[str, str]:
    raw, kind = _clean(value)
    figure = ChallengeFigure.objects.create(owner=teacher, content=raw, content_type=kind)
    return {"url": f"/api/v1/learning/figures/{figure.id}/"}


def visible_figure(user, figure_id) -> ChallengeFigure:
    try:
        figure = ChallengeFigure.objects.select_related("challenge").get(pk=figure_id)
    except (ChallengeFigure.DoesNotExist, ValueError, TypeError) as exc:
        raise DomainError(_MISSING, code="not_found", status_code=404) from exc
    if figure.content_type not in _KINDS:
        raise DomainError(_MISSING, code="not_found", status_code=404)
    if figure.owner_id == user.id:
        return figure
    challenge = figure.challenge
    if challenge is not None and challenge.is_published:
        return figure
    raise DomainError(_MISSING, code="not_found", status_code=404)


def attach_figures(challenge: Challenge, teacher) -> None:
    """Las imágenes que el enunciado nombra quedan ligadas a ese reto."""
    found = _FIGURE_IDS.findall(challenge.prompt)
    if not found:
        return
    ChallengeFigure.objects.filter(owner=teacher, pk__in=found).update(challenge=challenge)


def _clean(value: object) -> tuple[bytes, str]:
    if not isinstance(value, str) or not value.startswith("data:") or "," not in value:
        raise DomainError("La imagen no es válida.")
    header, encoded = value.split(",", 1)
    if ";base64" not in header:
        raise DomainError("La imagen no es válida.")
    kind = header[5:].split(";", 1)[0].lower()
    if kind == "image/jpg":
        kind = "image/jpeg"
    if kind not in _KINDS:
        raise DomainError("La imagen debe ser JPG, PNG, GIF o WEBP.")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise DomainError("La imagen no es válida.") from exc
    if len(raw) < 32 or len(raw) > _MAX_FIGURE or not _matches(kind, raw):
        raise DomainError("La imagen no es válida.")
    return raw, kind


def _matches(kind: str, raw: bytes) -> bool:
    if kind == "image/webp":
        return raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"
    return raw.startswith(_KINDS[kind])
