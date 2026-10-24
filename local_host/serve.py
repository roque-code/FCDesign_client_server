"""HTTP en 127.0.0.1. El canal de eventos usa el mismo sobre SSE que Django."""

from __future__ import annotations

import hmac
import json
import re
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from local_host.engine import Host, HostError
from local_host.entitlements import Entitlements, access_from_account
from local_host.proxy import ApiProxy

MAX_BODY = 1024 * 1024
_SESSION = re.compile(r"^/local/v1/sessions/([0-9a-f]+)$")
_SESSION_ACTION = re.compile(r"^/local/v1/sessions/([0-9a-f]+)/(control|input|inspect|events)$")
_LAB = re.compile(r"^/local/v1/lab/runs/([0-9a-f]+)$")
_LAB_ACTION = re.compile(r"^/local/v1/lab/runs/([0-9a-f]+)/(control|input|events)$")


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], token: str, api_origin: str) -> None:
        from local_host.foreign_run import remember_api_origin

        self.entitlements = Entitlements()
        self.host_engine = Host(self.entitlements)
        self.token = token
        self.proxy = ApiProxy(api_origin)
        remember_api_origin(api_origin)
        super().__init__(address, LocalHandler)


class LocalHandler(BaseHTTPRequestHandler):
    server: LocalServer
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(204, b"", "text/plain; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def _dispatch(self) -> None:
        if not self._authorized():
            self._error(401, "forbidden", "La orden local no está autorizada.")
            return
        split = urlsplit(self.path)
        path = split.path.rstrip("/") or "/"
        try:
            if self.command == "GET" and path == "/local/v1/health":
                self._json(200, {"ok": True})
                return
            if self.command == "POST" and path == "/local/v1/proxy":
                self._proxy()
                return
            if self.command == "POST" and path == "/local/v1/access":
                self._access()
                return
            body = self._json_body() if self.command == "POST" else {}
            if self.command == "POST" and path == "/local/v1/validate":
                self._json(200, self.server.host_engine.validate(body))
                return
            if self.command == "POST" and path == "/local/v1/translate":
                self._json(200, self.server.host_engine.translate(body))
                return
            if self.command == "POST" and path == "/local/v1/foreign/status":
                self._json(200, self.server.host_engine.foreign_status())
                return
            if self.command == "POST" and path == "/local/v1/foreign/run":
                self._json(200, self.server.host_engine.foreign_run(body))
                return
            if self.command == "POST" and path == "/local/v1/foreign/open":
                self._json(200, self.server.host_engine.foreign_open(body))
                return
            if self.command == "POST" and path == "/local/v1/foreign/input":
                self._json(200, self.server.host_engine.foreign_input(body))
                return
            if self.command == "POST" and path == "/local/v1/foreign/poll":
                self._json(200, self.server.host_engine.foreign_poll(body))
                return
            if self.command == "POST" and path == "/local/v1/foreign/close":
                self._json(200, self.server.host_engine.foreign_close(body))
                return
            if self.command == "POST" and path == "/local/v1/flowchart":
                self._json(200, self.server.host_engine.flowchart(body))
                return
            if self.command == "POST" and path == "/local/v1/sessions":
                self._json(201, self.server.host_engine.open_editor(body))
                return
            if self.command == "POST" and path == "/local/v1/lab/preview":
                self._json(200, self.server.host_engine.preview_lab(body))
                return
            if self.command == "POST" and path == "/local/v1/lab/import":
                self._json(200, self.server.host_engine.import_lab(body))
                return
            if self.command == "POST" and path == "/local/v1/lab/runs":
                self._json(201, self.server.host_engine.open_lab(body))
                return
            session = _SESSION.fullmatch(path)
            if session and self.command == "GET":
                self._json(200, self.server.host_engine.read_editor(session.group(1)))
                return
            action = _SESSION_ACTION.fullmatch(path)
            if action:
                self._session(action.group(1), action.group(2), body, split.query)
                return
            lab = _LAB.fullmatch(path)
            if lab and self.command == "GET":
                self._json(200, self.server.host_engine.read_lab(lab.group(1)))
                return
            lab_action = _LAB_ACTION.fullmatch(path)
            if lab_action:
                self._lab(lab_action.group(1), lab_action.group(2), body, split.query)
                return
        except HostError as exc:
            self._error(exc.status, exc.code, exc.message)
            return
        except (json.JSONDecodeError, UnicodeError):
            self._error(400, "invalid", "El cuerpo no es JSON.")
            return
        self._error(404, "not_found", "No existe esa orden local.")

    def _session(self, session_id: str, action: str, body: dict[str, Any], query: str) -> None:
        engine = self.server.host_engine
        if action == "events" and self.command == "GET":
            self._events(session_id, query)
            return
        if self.command != "POST":
            raise HostError("El método no es válido.")
        if action == "control":
            self._json(200, engine.control_editor(session_id, body))
            return
        if action == "input":
            self._json(200, engine.input_editor(session_id, body))
            return
        self._json(200, engine.inspect_editor(session_id, body))

    def _lab(self, session_id: str, action: str, body: dict[str, Any], query: str) -> None:
        engine = self.server.host_engine
        if action == "events" and self.command == "GET":
            self._events(session_id, query)
            return
        if self.command != "POST":
            raise HostError("El método no es válido.")
        if action == "control":
            self._json(200, engine.control_lab(session_id, body))
            return
        self._json(200, engine.input_lab(session_id, body))

    def _events(self, session_id: str, query: str) -> None:
        header = self.headers.get("Last-Event-ID", "0")
        try:
            after = int(header)
        except ValueError:
            after = 0
        once = parse_qs(query).get("once", ["0"])[0] == "1"
        frames = self.server.host_engine.stream(session_id, after, once=once)
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()
        self._write_frames(frames)

    def _write_frames(self, frames: Iterator[str]) -> None:
        try:
            for frame in frames:
                self.wfile.write(frame.encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def _proxy(self) -> None:
        body = self._json_body()
        path = body.get("path")
        method = body.get("method", "GET")
        raw = body.get("body")
        headers = body.get("headers")
        if not isinstance(path, str) or not isinstance(method, str):
            raise HostError("La ruta no es válida.")
        if raw is not None and not isinstance(raw, str):
            raise HostError("El cuerpo no es válido.")
        outbound = headers if isinstance(headers, dict) else {}
        clean = {str(key): value for key, value in outbound.items() if isinstance(value, str)}
        clean = {key: value for key, value in clean.items() if key.lower() != "x-traza-client"}
        clean["X-Aulivana-FCDdesign-Client"] = "desktop"
        status, payload, csrf = self.server.proxy.forward(
            path,
            method,
            raw.encode("utf-8") if isinstance(raw, str) else None,
            clean,
        )
        self._remember(path, status, payload)
        self._json(
            200, {"status": status, "body": payload.decode("utf-8", errors="replace"), "csrf": csrf}
        )

    def _access(self) -> None:
        body = self._json_body()
        access = body.get("access", body)
        if not isinstance(access, dict) or not isinstance(access.get("features"), dict):
            raise HostError("El nivel no es válido.")
        if not self.server.entitlements.has_trusted():
            self.server.entitlements.remember_hint(access)
        self._json(200, {"ok": True})

    def _remember(self, path: str, status: int, payload: bytes) -> None:
        if status < 200 or status >= 300 or not path.startswith("/api/v1/auth/"):
            return
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeError):
            return
        access = access_from_account(parsed)
        if access is not None:
            self.server.entitlements.remember_trusted(access)

    def _authorized(self) -> bool:
        query = parse_qs(urlsplit(self.path).query)
        provided = query.get("token", [""])[0]
        header = self.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            provided = header[7:].strip() or provided
        token = self.server.token
        if len(provided) != len(token):
            return False
        return _same(provided, token)

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0 or length > MAX_BODY:
            raise HostError("El cuerpo es demasiado grande.")
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise HostError("El cuerpo debe ser un objeto.")
        return parsed

    def _json(self, status: int, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, encoded, "application/json; charset=utf-8")

    def _error(self, status: int, code: str, message: str) -> None:
        self._json(status, {"error": {"code": code, "message": message}})

    def _send(self, status: int, payload: bytes, content_type: str) -> None:
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header(
            "Access-Control-Allow-Headers", "authorization, content-type, last-event-id"
        )
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Expose-Headers", "content-type")


def _same(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)
