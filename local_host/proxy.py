"""Reenvía al servidor de Aulivana-FCDdesign la sesión, el alta y la calificación.

La cookie queda en este proceso. El navegador de la ventana no tiene que
compartir origen con Django.
"""

from __future__ import annotations

import http.cookiejar
import threading
import urllib.error
import urllib.request

from local_host.engine import HostError
from local_host.foreign_run import ssl_context

_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "host",
        "content-length",
    }
)
_UNSAFE = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class ApiProxy:
    def __init__(self, origin: str) -> None:
        self.origin = origin.rstrip("/")
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar),
            urllib.request.HTTPSHandler(context=ssl_context()),
        )
        self._lock = threading.Lock()

    def forward(
        self, path: str, method: str, body: bytes | None, headers: dict[str, str]
    ) -> tuple[int, bytes, str]:
        if not path.startswith("/api/") or path.startswith("//") or "\\" in path:
            raise HostError("La ruta no es de la API.", code="not_found", status=404)
        url = f"{self.origin}{path}"
        chosen = method.upper()
        if chosen not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise HostError("El método no es válido.")
        outbound = {
            key: value
            for key, value in headers.items()
            if key.lower() not in _HOP and key.lower() != "authorization"
        }
        request_body = body if chosen != "GET" else None
        with self._lock:
            if chosen in _UNSAFE:
                self._prime_csrf()
                _stamp_origin(outbound, self.origin)
            _stamp_csrf(outbound, _csrf(self._jar))
            request = urllib.request.Request(
                url, data=request_body, headers=outbound, method=chosen
            )
            try:
                with self._opener.open(request, timeout=30) as response:
                    payload = response.read()
                    status = response.status
            except urllib.error.HTTPError as exc:
                payload = exc.read()
                status = exc.code
            except (urllib.error.URLError, TimeoutError) as exc:
                raise HostError("No se alcanzó el servidor.", code="conflict", status=409) from exc
            return status, payload, _csrf(self._jar)

    def _prime_csrf(self) -> None:
        """Pide la cookie si el arranque no alcanzó el servidor."""
        if _csrf(self._jar):
            return
        request = urllib.request.Request(f"{self.origin}/api/v1/auth/csrf/", method="GET")
        try:
            with self._opener.open(request, timeout=30) as response:
                response.read()
        except urllib.error.HTTPError as exc:
            exc.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            raise HostError("No se alcanzó el servidor.", code="conflict", status=409) from exc


def _stamp_origin(headers: dict[str, str], origin: str) -> None:
    """Por HTTPS, Django rechaza una escritura que no diga de qué sitio viene."""
    stale = [key for key in headers if key.lower() in {"origin", "referer"}]
    for key in stale:
        del headers[key]
    headers["Origin"] = origin
    headers["Referer"] = f"{origin}/"


def _stamp_csrf(headers: dict[str, str], token: str) -> None:
    if not token:
        return
    stale = [key for key in headers if key.lower() == "x-csrftoken"]
    for key in stale:
        del headers[key]
    headers["X-CSRFToken"] = token


def _csrf(jar: http.cookiejar.CookieJar) -> str:
    for cookie in jar:
        if cookie.name == "csrftoken" and cookie.value:
            return cookie.value
    return ""
