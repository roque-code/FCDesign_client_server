"""Salidas de la plataforma durante un examen, un reto o un ejercicio. Avisa y registra; no bloquea."""

from __future__ import annotations

from datetime import datetime

from config.errors import DomainError

EVENTS = ("leave", "back", "fullscreen", "paste")
REASONS = ("hidden", "blur")
MAX_EVENTS = 200


def focus_start(rules: dict[str, object]) -> dict[str, object]:
    if not rules.get("watched"):
        return {}
    return {
        "watched": True,
        "limit": rules.get("limit"),
        "exits": 0,
        "away_seconds": 0,
        "fullscreen_exits": 0,
        "pastes": 0,
        "left_at": None,
        "events": [],
        "auto_submitted": False,
    }


def watching(focus: object) -> bool:
    return isinstance(focus, dict) and focus.get("watched") is True


def _count(focus: dict, key: str) -> int:
    value = focus.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def focus_report(focus: object, until: datetime | None) -> dict[str, object] | None:
    """Resumen para el alumno y el docente. `until` cierra una salida todavía abierta."""
    if not isinstance(focus, dict) or not watching(focus):
        return None
    away = _count(focus, "away_seconds")
    left_at = focus.get("left_at")
    if isinstance(left_at, (int, float)) and until is not None:
        away += max(0, round(until.timestamp() - left_at))
    limit = focus.get("limit")
    return {
        "limit": limit if isinstance(limit, int) else None,
        "exits": _count(focus, "exits"),
        "away_seconds": away,
        "fullscreen_exits": _count(focus, "fullscreen_exits"),
        "pastes": _count(focus, "pastes"),
        "away_now": isinstance(left_at, (int, float)),
        "auto_submitted": focus.get("auto_submitted") is True,
    }


def away_text(seconds: int) -> str:
    minutes, rest = divmod(seconds, 60)
    return f"{minutes} min {rest} s" if minutes else f"{rest} s"


def focus_event(data: dict, extra: tuple[str, ...] = ()) -> tuple[str, str]:
    event = data.get("event")
    if event not in EVENTS and event not in extra:
        raise DomainError("El evento no es válido.")
    reason = data.get("reason")
    return str(event), reason if reason in REASONS else ""


def apply_event(focus: dict, event: str, reason: str, now: datetime) -> tuple[dict, bool]:
    """Devuelve el registro nuevo y si la salida alcanzó el límite del grupo."""
    focus = dict(focus)
    events = list(focus.get("events") or [])
    stamp = now.isoformat()
    reached = False
    if event == "leave":
        if focus.get("left_at") is None:
            focus["exits"] = _count(focus, "exits") + 1
            focus["left_at"] = now.timestamp()
            events.append({"kind": "leave", "reason": reason, "at": stamp})
            limit = focus.get("limit")
            reached = isinstance(limit, int) and focus["exits"] >= limit
    elif event == "back":
        left_at = focus.get("left_at")
        if isinstance(left_at, (int, float)):
            seconds = max(0, round(now.timestamp() - left_at))
            focus["away_seconds"] = _count(focus, "away_seconds") + seconds
            focus["left_at"] = None
            events.append({"kind": "back", "at": stamp, "seconds": seconds})
    elif event == "open":
        # Una salida sin regreso de una visita anterior: cuenta la salida, no el tiempo.
        focus["left_at"] = None
    elif event == "fullscreen":
        focus["fullscreen_exits"] = _count(focus, "fullscreen_exits") + 1
        events.append({"kind": "fullscreen", "at": stamp})
    else:
        focus["pastes"] = _count(focus, "pastes") + 1
        events.append({"kind": "paste", "at": stamp})
    focus["events"] = events[-MAX_EVENTS:]
    return focus, reached


def close_focus(focus: dict, now: datetime) -> dict:
    """Entrega automática: la salida en curso cuenta hasta este momento."""
    focus, _ = apply_event(focus, "back", "", now)
    focus["auto_submitted"] = True
    return focus
