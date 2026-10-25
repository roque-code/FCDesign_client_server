"""Un solo proceso para ejecutar lenguajes del navegador.

Gunicorn tiene varios workers. Una sesión que espera un dato vive en este
proceso, así la siguiente petición encuentra el programa.
"""

from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from local_host.engine import Host, HostError
from local_host.foreign_run import remember_api_origin

MAX_BODY = 1024 * 1024
TOKEN_FILE = Path("/tmp/traza-language.token")


class LanguageServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], token: str) -> None:
        self.token = token
        self.engine = Host(None)
        super().__init__(address, LanguageHandler)


class LanguageHandler(BaseHTTPRequestHandler):
    server: LanguageServer
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def _dispatch(self) -> None:
        if not self._authorized():
            self._error(401, "forbidden", "La orden local no está autorizada.")
            return
        path = urlsplit(self.path).path.rstrip("/") or "/"
        try:
            if self.command == "GET" and path == "/local/v1/health":
                self._json(200, {"ok": True})
                return
            if self.command != "POST":
                self._error(404, "not_found", "No existe esa orden local.")
                return
            body = self._json_body()
            engine = self.server.engine
            if path == "/local/v1/foreign/status":
                self._json(200, engine.foreign_status())
                return
            if path == "/local/v1/foreign/run":
                self._json(200, engine.foreign_run(_browser_flags(body)))
                return
            if path == "/local/v1/foreign/open":
                self._json(200, engine.foreign_open(_browser_flags(body)))
                return
            if path == "/local/v1/foreign/input":
                self._json(200, engine.foreign_input(body))
                return
            if path == "/local/v1/foreign/poll":
                self._json(200, engine.foreign_poll(body))
                return
            if path == "/local/v1/foreign/close":
                self._json(200, engine.foreign_close(body))
                return
        except HostError as exc:
            self._error(exc.status, exc.code, exc.message)
            return
        except (json.JSONDecodeError, UnicodeError):
            self._error(400, "invalid", "El cuerpo no es JSON.")
            return
        except OSError as exc:
            detail = exc.strerror or str(exc)
            message = f"No se pudo ejecutar. {detail}" if detail else "No se pudo ejecutar."
            self._error(500, "invalid", message)
            return
        self._error(404, "not_found", "No existe esa orden local.")

    def _authorized(self) -> bool:
        query = parse_qs(urlsplit(self.path).query)
        provided = query.get("token", [""])[0]
        header = self.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            provided = header[7:].strip() or provided
        token = _current_token() or self.server.token
        if len(provided) != len(token):
            return False
        return hmac.compare_digest(provided, token)

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0 or length > MAX_BODY:
            raise HostError("El cuerpo es demasiado grande.")
        if length == 0:
            return {}
        parsed = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(parsed, dict):
            raise HostError("El cuerpo debe ser un objeto.")
        return parsed

    def _json(self, status: int, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _error(self, status: int, code: str, message: str) -> None:
        self._json(status, {"error": {"code": code, "message": message}})


def _current_token() -> str:
    try:
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return os.environ.get("TRAZA_LANGUAGE_TOKEN", "").strip()


def _browser_flags(body: dict[str, Any]) -> dict[str, Any]:
    """El navegador siempre corre aislado y puede descargar el runtime."""
    merged = dict(body)
    merged["download"] = True
    merged["isolated"] = True
    return merged


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    manifest = root / "deploy" / "runtimes" / "manifest.json"
    if manifest.is_file() and not os.environ.get("TRAZA_RUNTIME_MANIFEST", "").strip():
        os.environ["TRAZA_RUNTIME_MANIFEST"] = str(manifest)
    origin = os.environ.get("TRAZA_PUBLIC_ORIGIN", "").strip()
    if origin:
        remember_api_origin(origin)
    token = _current_token()
    if not token:
        raise SystemExit("Falta TRAZA_LANGUAGE_TOKEN.")
    port = int(os.environ.get("TRAZA_LANGUAGE_PORT", "8766"))
    LanguageServer(("127.0.0.1", port), token).serve_forever()


if __name__ == "__main__":
    main()
