"""Puente entre Django y el runner. El intérprete no vive en este proceso."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator

import redis
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from runner.protocol import (
    HEARTBEAT,
    JOBS,
    STATE_TTL,
    TERMINAL_EVENTS,
    TERMINAL_STATUS,
    cmd_key,
    events_key,
    meta_key,
    reply_key,
    signal_key,
    sse_frame,
    state_key,
    user_key,
    wake_key,
)

_redis: redis.Redis | None = None


class BusRejected(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BusTimeout(Exception):
    def __init__(self) -> None:
        super().__init__("El ejecutor no respondió.")
        self.message = "El ejecutor no respondió."


def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        url = settings.REDIS_URL
        if not url:
            raise ImproperlyConfigured("TRAZA_RUNNER=redis exige REDIS_URL.")
        _redis = redis.Redis.from_url(url, decode_responses=True)
    return _redis


def heartbeat_ok() -> bool:
    try:
        return bool(get_redis().get(HEARTBEAT))
    except redis.RedisError:
        return False


def drop_kind(user_id: int, kind: str) -> None:
    client = get_redis()
    key = user_key(user_id, kind)
    for raw in client.smembers(key):
        execution_id = raw.decode() if isinstance(raw, bytes) else str(raw)
        client.rpush(signal_key(execution_id), json.dumps({"op": "stop"}))
        client.rpush(cmd_key(execution_id), json.dumps({"op": "close"}))
    client.delete(key)


def launch(
    *,
    user_id: int,
    source: str,
    profile: dict[str, object],
    breakpoints: set[int],
    interactive: bool,
    kind: str,
    bindings: list[dict[str, object]] | None = None,
    execution_id: str | None = None,
) -> dict[str, object]:
    client = get_redis()
    chosen = execution_id or str(uuid.uuid4())
    token = str(uuid.uuid4())
    meta = {
        "user_id": user_id,
        "kind": kind,
        "interactive": interactive,
        "source": source,
        "bindings": bindings or [],
    }
    client.set(meta_key(chosen), json.dumps(meta, ensure_ascii=False), ex=STATE_TTL)
    client.sadd(user_key(user_id, kind), chosen)
    client.expire(user_key(user_id, kind), STATE_TTL)
    job = {
        "id": chosen,
        "source": source,
        "profile": profile,
        "breakpoints": sorted(breakpoints),
        "reply": token,
        "interactive": interactive,
    }
    client.rpush(JOBS, json.dumps(job, ensure_ascii=False))
    state = _wait(client, token)
    state["id"] = chosen
    return state


def command(execution_id: str, op: str, **fields: object) -> dict[str, object]:
    client = get_redis()
    token = str(uuid.uuid4())
    body: dict[str, object] = {"op": op, "reply": token, **fields}
    client.rpush(cmd_key(execution_id), json.dumps(body, ensure_ascii=False))
    state = _wait(client, token)
    state["id"] = execution_id
    return state


def inspect(execution_id: str, name: str, start: int, count: int) -> dict[str, object]:
    client = get_redis()
    token = str(uuid.uuid4())
    body = {"op": "inspect", "reply": token, "name": name, "start": start, "count": count}
    client.rpush(cmd_key(execution_id), json.dumps(body))
    item = client.blpop([reply_key(token)], timeout=15)
    if item is None:
        raise BusTimeout()
    payload = json.loads(item[1])
    if not payload.get("ok"):
        raise BusRejected(str(payload.get("message") or "La orden no es válida."))
    inspected = payload.get("inspect")
    if not isinstance(inspected, dict):
        raise BusRejected("El arreglo no es válido.")
    return inspected


def signal(execution_id: str, op: str) -> None:
    get_redis().rpush(signal_key(execution_id), json.dumps({"op": op}))


def fetch_state(execution_id: str) -> dict[str, object] | None:
    raw = get_redis().get(state_key(execution_id))
    if not isinstance(raw, str):
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        return None
    data["id"] = execution_id
    return data


def load_meta(execution_id: str) -> dict[str, object] | None:
    raw = get_redis().get(meta_key(execution_id))
    if not isinstance(raw, str):
        return None
    data = json.loads(raw)
    return data if isinstance(data, dict) else None


def iter_events(execution_id: str, after: int, *, once: bool) -> Iterator[str]:
    client = get_redis()
    pubsub = client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(wake_key(execution_id))
    cursor = after
    try:
        while True:
            terminal = False
            for raw in client.lrange(events_key(execution_id), 0, -1):
                event = json.loads(raw)
                if not isinstance(event, dict):
                    continue
                number = event.get("id")
                if not isinstance(number, int) or number <= cursor:
                    continue
                cursor = number
                yield sse_frame(event, execution_id)
                if event.get("event") in TERMINAL_EVENTS:
                    terminal = True
            if once or terminal:
                return
            incoming = pubsub.get_message(timeout=15)
            if incoming is None:
                yield ": keepalive\n\n"
                current = fetch_state(execution_id)
                if current is not None and current.get("status") in TERMINAL_STATUS:
                    return
    finally:
        pubsub.close()


def _wait(client: redis.Redis, token: str) -> dict[str, object]:
    item = client.blpop([reply_key(token)], timeout=15)
    if item is None:
        raise BusTimeout()
    payload = json.loads(item[1])
    if not isinstance(payload, dict) or not payload.get("ok"):
        message = payload.get("message") if isinstance(payload, dict) else None
        raise BusRejected(str(message or "La orden no es válida."))
    state = payload.get("state")
    if not isinstance(state, dict):
        raise BusRejected("El ejecutor no devolvió el estado.")
    return state
