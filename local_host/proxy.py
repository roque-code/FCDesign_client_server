"""Reenvía al servidor de Traza la sesión, el alta y la calificación.

La cookie queda en este proceso. El navegador de la ventana no tiene que
compartir origen con Django.
"""

from __future__ import annotations

import http.cookiejar
import threading
import urllib.error
import urllib.request

from local_host.engine import HostError

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


class ApiProxy:
    def __init__(self, origin: str) -> None:
        self.origin = origin.rstrip("/")
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self._jar))
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
            token = _csrf(self._jar)
            if (
                token
                and "X-CSRFToken" not in outbound
                and not any(key.lower() == "x-csrftoken" for key in outbound)
            ):
                outbound["X-CSRFToken"] = token
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


def _csrf(jar: http.cookiejar.CookieJar) -> str:
    for cookie in jar:
        if cookie.name == "csrftoken" and cookie.value:
            return cookie.value
    return ""
