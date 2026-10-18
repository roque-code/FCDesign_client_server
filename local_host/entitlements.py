"""El nivel que el motor local ya conoce. No consulta al servidor en cada orden."""

from __future__ import annotations

import threading
from typing import Any


class Entitlements:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._trusted: dict[str, Any] | None = None
        self._hint: dict[str, Any] | None = None

    def remember_trusted(self, access: dict[str, Any]) -> None:
        with self._lock:
            self._trusted = access

    def remember_hint(self, access: dict[str, Any]) -> None:
        with self._lock:
            self._hint = access

    def has_trusted(self) -> bool:
        with self._lock:
            return self._trusted is not None

    def allows(self, *keys: str) -> bool:
        with self._lock:
            current = self._trusted if self._trusted is not None else self._hint
        if current is None:
            return True
        features = current.get("features")
        if not isinstance(features, dict):
            return False
        return any(features.get(key) is True for key in keys)


def access_from_account(payload: object) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    access = payload.get("access")
    if not isinstance(access, dict) or not isinstance(access.get("features"), dict):
        return None
    return access
