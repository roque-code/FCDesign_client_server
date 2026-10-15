"""Consume órdenes en Redis y publica eventos. Una sesión, un hilo."""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from typing import Any

import redis

from language_core.debugger import DebugRejected, open_debug
from language_core.grammar import profile_from_mapping
from runner.protocol import (
    HEARTBEAT,
    JOBS,
    STATE_TTL,
    TERMINAL_STATUS,
    cmd_key,
    diagnostic_to_json,
    event_for_wire,
    events_key,
    lock_key,
    reply_key,
    signal_key,
    state_key,
    wake_key,
)

MAX_SOURCE = 64 * 1024
MAX_SESSIONS = 32


def main() -> None:
    url = os.environ.get("REDIS_URL", "")
    if not url:
        print("REDIS_URL es obligatorio para el runner.", file=sys.stderr)
        raise SystemExit(1)
    client = redis.Redis.from_url(url, decode_responses=True)
    stop = threading.Event()

    def request_stop(signum: int, _frame: object) -> None:
        print(f"runner: señal {signum}, cerrando.", file=sys.stderr)
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    run_worker(client, stop)


def run_worker(client: redis.Redis, stop: threading.Event) -> None:
    threading.Thread(target=_beat, args=(client, stop), name="traza-heartbeat", daemon=True).start()
    slots = threading.Semaphore(MAX_SESSIONS)
    while not stop.is_set():
        item = client.blpop([JOBS], timeout=1)
        if item is None:
            continue
        try:
            job = json.loads(item[1])
        except json.JSONDecodeError:
            print("runner: orden ilegible.", file=sys.stderr)
            continue
        if not isinstance(job, dict):
            continue
        if not slots.acquire(blocking=False):
            client.rpush(JOBS, item[1])
            time.sleep(0.2)
            continue
        threading.Thread(
            target=_guarded,
            args=(client, job, slots),
            name=f"traza-{job.get('id', 'sesion')}",
            daemon=True,
        ).start()


def _beat(client: redis.Redis, stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            client.set(HEARTBEAT, str(time.time()), ex=6)
        except redis.RedisError as exc:
            print(f"runner: latido falló: {exc}", file=sys.stderr)
        stop.wait(2)


def _guarded(client: redis.Redis, job: dict[str, Any], slots: threading.Semaphore) -> None:
    try:
        _session(client, job)
    except Exception as exc:
        print(f"runner: la sesión falló: {exc}", file=sys.stderr)
        token = job.get("reply")
        if isinstance(token, str):
            _reply(client, token, {"ok": False, "message": "El ejecutor falló."})
    finally:
        slots.release()


def _session(client: redis.Redis, job: dict[str, Any]) -> None:
    execution_id = job.get("id")
    source = job.get("source")
    profile_data = job.get("profile")
    if not isinstance(execution_id, str) or not isinstance(source, str):
        return
    if not isinstance(profile_data, dict):
        profile_data = {}
    if len(source) > MAX_SOURCE:
        _reply(client, _token(job), {"ok": False, "message": "El algoritmo es demasiado largo."})
        return
    claimed = client.set(lock_key(execution_id), "1", nx=True, ex=30)
    if not claimed:
        _reply(client, _token(job), {"ok": False, "message": "Esa ejecución ya tiene un runner."})
        return
    name = profile_data.get("profile_key") or profile_data.get("name") or "strict"
    profile = profile_from_mapping(str(name), profile_data)
    marks = _lines(job.get("breakpoints"))
    holder: dict[str, Any] = {
        "session": open_debug(source, profile, marks),
        "busy": False,
        "closed": False,
        "source": source,
        "profile": profile,
        "interactive": bool(job.get("interactive")),
        "seq": 0,
        "seen": {},
    }
    holder["session"].flush = lambda: _flush(client, execution_id, holder)
    _flush(client, execution_id, holder)
    _reply(client, _token(job), {"ok": True, "state": _state(holder)})
    threading.Thread(
        target=_signals,
        args=(client, execution_id, holder),
        name=f"traza-signal-{execution_id}",
        daemon=True,
    ).start()
    idle = 0
    try:
        while not holder["closed"]:
            client.expire(lock_key(execution_id), 30)
            item = client.blpop([cmd_key(execution_id)], timeout=2)
            if item is None:
                status = holder["session"].status
                if status in TERMINAL_STATUS:
                    idle += 2
                    if idle >= 30:
                        break
                continue
            idle = 0
            try:
                command = json.loads(item[1])
            except json.JSONDecodeError:
                continue
            if not isinstance(command, dict):
                continue
            if command.get("op") == "close":
                holder["closed"] = True
                holder["session"].close()
                break
            _apply(client, execution_id, holder, command)
    finally:
        holder["closed"] = True
        client.delete(lock_key(execution_id))


def _signals(client: redis.Redis, execution_id: str, holder: dict[str, Any]) -> None:
    while not holder["closed"]:
        item = client.blpop([signal_key(execution_id)], timeout=1)
        if item is None or holder["closed"]:
            continue
        try:
            command = json.loads(item[1])
        except json.JSONDecodeError:
            continue
        if not isinstance(command, dict):
            continue
        session = holder["session"]
        if command.get("op") == "pause":
            session.pause_requested = True
        elif command.get("op") == "stop":
            session.stop_requested = True
            cancel = getattr(session.interpreter, "cancellation", None)
            if cancel is not None:
                cancel.cancel()


def _apply(
    client: redis.Redis, execution_id: str, holder: dict[str, Any], command: dict[str, Any]
) -> None:
    op = command.get("op")
    raw_token = command.get("reply")
    token = raw_token if isinstance(raw_token, str) else ""
    session = holder["session"]
    try:
        marks = command.get("breakpoints")
        if marks is not None:
            session.set_breakpoints(_lines(marks))
        holder["busy"] = True
        if op == "input":
            text = command.get("text")
            if not isinstance(text, str):
                raise DebugRejected("El dato no es válido.")
            session.provide_input(text)
        elif op == "restart":
            session.close()
            fresh = open_debug(holder["source"], holder["profile"], set(session.breakpoints))
            fresh.flush = lambda: _flush(client, execution_id, holder)
            holder["session"] = fresh
        elif op == "inspect":
            name = command.get("name")
            start = command.get("start")
            count = command.get("count")
            if (
                not isinstance(name, str)
                or isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(count, bool)
                or not isinstance(count, int)
            ):
                raise DebugRejected("El arreglo no es válido.")
            inspected = session.inspect(name, start, count)
            _flush(client, execution_id, holder)
            _reply(client, token, {"ok": True, "inspect": inspected, "state": _state(holder)})
            return
        elif op == "breakpoints":
            pass
        elif op in ("step", "step_in", "step_out", "continue", "stop"):
            session.command(str(op))
        else:
            raise DebugRejected("La orden no es válida.")
        _flush(client, execution_id, holder)
        _reply(client, token, {"ok": True, "state": _state(holder)})
    except DebugRejected as exc:
        _reply(client, token, {"ok": False, "message": exc.message})
    finally:
        holder["busy"] = False


def _flush(client: redis.Redis, execution_id: str, holder: dict[str, Any]) -> None:
    session = holder["session"]
    seen: dict[int, int] = holder["seen"]
    key = id(session)
    published = seen.get(key, 0)
    fresh = session.events[published:]
    seen[key] = len(session.events)
    if fresh:
        pipe = client.pipeline()
        event_key = events_key(execution_id)
        for event in fresh:
            holder["seq"] += 1
            stored = event_for_wire(event)
            stored["id"] = holder["seq"]
            pipe.rpush(event_key, json.dumps(stored, ensure_ascii=False))
        pipe.expire(event_key, STATE_TTL)
        pipe.publish(wake_key(execution_id), "1")
        pipe.execute()
    encoded = json.dumps(_state(holder), ensure_ascii=False)
    client.set(state_key(execution_id), encoded, ex=STATE_TTL)


def _state(holder: dict[str, Any]) -> dict[str, object]:
    session = holder["session"]
    snap = session.snapshot()
    diagnostics = snap.get("diagnostics")
    rows = diagnostics if isinstance(diagnostics, tuple) else ()
    return {
        "status": snap["status"],
        "line": snap["line"],
        "column": snap["column"],
        "scope": snap["scope"],
        "variables": snap["variables"],
        "call_stack": snap["call_stack"],
        "output": snap["output"],
        "diagnostics": [diagnostic_to_json(item) for item in rows],
        "pending_input": snap["pending_input"],
        "last_condition": snap["last_condition"],
        "instruction_count": snap["instruction_count"],
        "breakpoints": snap["breakpoints"],
        "event_cursor": holder["seq"],
        "inputs": list(session.inputs),
        "interactive": holder["interactive"],
    }


def _reply(client: redis.Redis, token: str, payload: dict[str, object]) -> None:
    if not token:
        return
    key = reply_key(token)
    client.rpush(key, json.dumps(payload, ensure_ascii=False))
    client.expire(key, 30)


def _token(job: dict[str, Any]) -> str:
    token = job.get("reply")
    return token if isinstance(token, str) else ""


def _lines(value: object) -> set[int]:
    if not isinstance(value, list):
        return set()
    return {
        item for item in value if isinstance(item, int) and not isinstance(item, bool) and item > 0
    }
