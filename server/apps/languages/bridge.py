"""El navegador ejecuta en el servidor. La sesión vive en un solo proceso."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from config.errors import DomainError

_engine = None
_host_ready = False


class _HostDown(Exception):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _ensure_local_host() -> None:
    root = Path(__file__).resolve().parents[3]
    text = str(root)
    if text not in sys.path:
        sys.path.insert(0, text)


def _host_is_external() -> bool:
    """En el servidor el lenguaje corre en su contenedor, no en este proceso."""
    return os.environ.get("TRAZA_LANGUAGE_HOST", "1").strip() == "0"


def dispatch(action: str, body: dict[str, Any]) -> dict[str, object]:
    _ensure_local_host()
    from local_host.engine import HostError

    payload = dict(body)
    if action in {"run", "open"}:
        payload["download"] = True
        payload["isolated"] = True
    try:
        if _host_is_external():
            return _post_external(action, payload)
        if _use_host():
            try:
                return _post(f"/local/v1/foreign/{action}", payload)
            except _HostDown:
                pass
        return _direct(action, payload)
    except HostError as exc:
        raise DomainError(exc.message, code=exc.code, status_code=exc.status) from exc


def _post_external(action: str, payload: dict[str, Any]) -> dict[str, object]:
    if not _token():
        raise DomainError("Lenguajes no está disponible.", code="unavailable", status_code=503)
    try:
        return _post(f"/local/v1/foreign/{action}", payload)
    except _HostDown as exc:
        raise DomainError("Lenguajes no está disponible.", code="unavailable", status_code=503) from exc


def _token() -> str:
    env = os.environ.get("TRAZA_LANGUAGE_TOKEN", "").strip()
    if env:
        return env
    try:
        return Path("/tmp/traza-language.token").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _use_host() -> bool:
    global _host_ready
    if _host_ready:
        return True
    token = _token()
    if not token:
        return False
    origin = _origin()
    url = f"{origin}/local/v1/health?token={urllib.parse.quote(token)}"
    try:
        with urllib.request.urlopen(url, timeout=0.3) as response:
            _host_ready = response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
    return _host_ready


def _origin() -> str:
    port = os.environ.get("TRAZA_LANGUAGE_PORT", "8766").strip() or "8766"
    return os.environ.get("TRAZA_LANGUAGE_ORIGIN", f"http://127.0.0.1:{port}").rstrip("/")


def _post(path: str, body: dict[str, Any]) -> dict[str, object]:
    token = _token()
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{_origin()}{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed: object
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as decode_error:
            raise _HostDown("No se pudo ejecutar.") from decode_error
        error = parsed.get("error") if isinstance(parsed, dict) else None
        if isinstance(error, dict):
            message = error.get("message")
            code = error.get("code")
            raise DomainError(
                message if isinstance(message, str) and message else "No se pudo ejecutar.",
                code=code if isinstance(code, str) and code else "invalid",
                status_code=exc.code if isinstance(exc.code, int) else 400,
            ) from exc
        raise DomainError("No se pudo ejecutar.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        detail = exc.strerror if isinstance(exc, OSError) and exc.strerror else ""
        raise _HostDown(f"No se pudo ejecutar. {detail}".strip()) from exc
    if not isinstance(payload, dict):
        raise _HostDown("No se pudo ejecutar.")
    return payload


def _gevent_patched() -> bool:
    try:
        from gevent.monkey import is_module_patched
    except ImportError:
        return False
    return is_module_patched("threading")


def _direct(action: str, body: dict[str, Any]) -> dict[str, object]:
    _ensure_local_host()
    engine = _local_engine()
    if action == "status":
        return engine.foreign_status()
    # Dentro de gunicorn el hilo de la sesión se vuelve un greenlet y no avanza.
    if action in {"run", "open"} and _gevent_patched():
        result = dict(engine.foreign_run(body))
        result.setdefault("session", "")
        return result
    if action == "run":
        return engine.foreign_run(body)
    if action == "open":
        return engine.foreign_open(body)
    if action == "input":
        return engine.foreign_input(body)
    if action == "poll":
        return engine.foreign_poll(body)
    if action == "close":
        return engine.foreign_close(body)
    raise DomainError("No se pudo ejecutar.")


def _local_engine():
    global _engine
    if _engine is None:
        from local_host.engine import Host

        _engine = Host(None)
    return _engine
