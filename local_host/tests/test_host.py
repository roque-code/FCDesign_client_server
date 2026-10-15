"""El proceso local compila, depura y emite el mismo sobre SSE."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from local_host.proxy import ApiProxy
from local_host.serve import LocalServer

SOURCE = """Algoritmo Demo
    Definir n Como Entero;
    n <- 1;
    n <- 2;
    Escribir n;
FinAlgoritmo
"""

TOKEN = "token-de-prueba"


def _server() -> tuple[LocalServer, str]:
    server = LocalServer(("127.0.0.1", 0), TOKEN, "http://127.0.0.1:9")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    bound = server.server_address
    raw_host = bound[0]
    host = raw_host.decode("ascii") if isinstance(raw_host, bytes) else str(raw_host)
    port = bound[1]
    return server, f"http://{host}:{port}"


def _call(
    origin: str, method: str, path: str, body: dict[str, object] | None = None, token: str = TOKEN
) -> tuple[int, Any]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        f"{origin}{path}",
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(request) as response:
        return response.status, json.loads(response.read().decode())


def test_validate_flowchart_and_debug_use_the_same_event_envelope() -> None:
    server, origin = _server()
    try:
        status, checked = _call(
            origin, "POST", "/local/v1/validate", {"source": SOURCE, "profile": {}}
        )
        assert status == 200
        assert all(item["severity"] != "error" for item in checked["diagnostics"])

        status, graph = _call(
            origin, "POST", "/local/v1/flowchart", {"source": SOURCE, "profile": {}}
        )
        assert status == 200
        assert graph["graph"]["entry"]
        assert graph["graph"]["nodes"]

        status, opened = _call(
            origin,
            "POST",
            "/local/v1/sessions",
            {
                "source": SOURCE,
                "profile": {"profile_key": "strict"},
                "breakpoints": [],
                "interactive": True,
            },
        )
        assert status == 201
        assert opened["debug"] is True
        assert opened["status"] == "paused"
        session_id = opened["id"]

        frame_request = urllib.request.Request(
            f"{origin}/local/v1/sessions/{session_id}/events/?once=1&token={TOKEN}"
        )
        with urllib.request.urlopen(frame_request) as response:
            frame = response.read().decode()
        first = frame.split("\n\n", 1)[0]
        assert first.startswith("id: ")
        assert "\nevent: paused\n" in first
        payload = json.loads(first.split("data: ", 1)[1])
        assert payload["execution_id"] == session_id
        assert "output" not in payload

        status, stepped = _call(
            origin,
            "POST",
            f"/local/v1/sessions/{session_id}/control",
            {"action": "continue"},
        )
        assert status == 200
        assert stepped["status"] == "completed"
        assert "2" in stepped["output"]
    finally:
        server.shutdown()


def test_a_missing_token_is_rejected_and_lab_import_stays_local() -> None:
    server, origin = _server()
    try:
        request = urllib.request.Request(
            f"{origin}/local/v1/validate",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(request)
            raise AssertionError("debía rechazar la orden")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401

        status, imported = _call(
            origin,
            "POST",
            "/local/v1/lab/import",
            {"source": "Algoritmo Demo\nFinAlgoritmo\n"},
        )
        assert status == 200
        assert isinstance(imported["workspace"], dict)
    finally:
        server.shutdown()


def test_the_proxy_refuses_paths_outside_the_api() -> None:
    server, origin = _server()
    try:
        try:
            _call(
                origin, "POST", "/local/v1/proxy", {"path": "http://ejemplo.test/", "method": "GET"}
            )
            raise AssertionError("debía rechazar la ruta")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
    finally:
        server.shutdown()


class _CsrfApi(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        body = b'{"ok":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Set-Cookie", "csrftoken=token-fijo; Path=/")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        cookie = self.headers.get("Cookie", "")
        token = self.headers.get("X-CSRFToken", "")
        ok = cookie == "csrftoken=token-fijo" and token == "token-fijo"
        body = b'{"ok":true}' if ok else b'{"error":"csrf"}'
        self.send_response(200 if ok else 403)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_an_unsafe_call_fetches_csrf_when_the_jar_is_empty() -> None:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _CsrfApi)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        port = httpd.server_address[1]
        proxy = ApiProxy(f"http://127.0.0.1:{port}")
        status, payload, csrf = proxy.forward(
            "/api/v1/auth/login/",
            "POST",
            b"{}",
            {"X-CSRFToken": ""},
        )
        assert status == 200
        assert json.loads(payload) == {"ok": True}
        assert csrf == "token-fijo"
    finally:
        httpd.shutdown()
