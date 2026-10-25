"""Ponderación de la nota. Suma 100. Vacío significa la rúbrica por defecto."""

from __future__ import annotations

from typing import Any

from config.errors import DomainError

WEIGHT_KEYS = (
    "comprension",
    "diseno",
    "correccion",
    "lenguaje",
    "explicacion",
    "autonomia",
)

DEFAULT_WEIGHTS = {
    "comprension": 20,
    "diseno": 25,
    "correccion": 30,
    "lenguaje": 0,
    "explicacion": 15,
    "autonomia": 10,
}

LANGUAGE_WEIGHTS = {
    "comprension": 15,
    "diseno": 20,
    "correccion": 20,
    "lenguaje": 20,
    "explicacion": 15,
    "autonomia": 10,
}


def default_weights(*, language: bool) -> dict[str, int]:
    return dict(LANGUAGE_WEIGHTS if language else DEFAULT_WEIGHTS)


def filled_weights(raw: object) -> dict[str, int] | None:
    if not isinstance(raw, dict) or not raw:
        return None
    values: dict[str, int] = {}
    for key in WEIGHT_KEYS:
        item = raw.get(key)
        if isinstance(item, bool) or not isinstance(item, int) or item < 0 or item > 100:
            return None
        values[key] = item
    if sum(values.values()) != 100:
        return None
    return values


def parse_weights(raw: object, *, allow_language: bool) -> dict[str, int]:
    if raw is None or raw == "" or raw == {}:
        return {}
    if not isinstance(raw, dict):
        raise DomainError("Las ponderaciones no son válidas.")
    extra = set(raw) - set(WEIGHT_KEYS)
    if extra:
        raise DomainError("Hay una ponderación que no existe.")
    missing = [key for key in WEIGHT_KEYS if key not in raw]
    if missing:
        raise DomainError("Faltan ponderaciones de la calificación.")
    values: dict[str, int] = {}
    for key in WEIGHT_KEYS:
        item = raw[key]
        if isinstance(item, bool) or not isinstance(item, int) or item < 0 or item > 100:
            raise DomainError("Cada ponderación va de 0 a 100.")
        values[key] = item
    if not allow_language and values["lenguaje"] != 0:
        raise DomainError("Este reto no evalúa un lenguaje.")
    if sum(values.values()) != 100:
        raise DomainError("Las ponderaciones tienen que sumar 100.")
    return values


def challenge_uses_language(challenge: Any) -> bool:
    if getattr(challenge, "activity_type", None) != "build":
        return False
    cases = getattr(challenge, "test_cases", None)
    if cases is None:
        return False
    cache = getattr(challenge, "_prefetched_objects_cache", None)
    if isinstance(cache, dict) and "test_cases" in cache:
        return len(list(cases.all())) > 0
    return cases.exists()


def resolved_weights(challenge: Any, entry: Any = None) -> dict[str, int]:
    if entry is not None:
        stored = filled_weights(getattr(entry, "weights", None))
        if stored is not None:
            return stored
    stored = filled_weights(getattr(challenge, "weights", None))
    if stored is not None:
        return stored
    return default_weights(language=challenge_uses_language(challenge))
