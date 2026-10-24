"""El editor de otros lenguajes corre en la máquina y no toca el pseudocódigo."""

from __future__ import annotations

import hashlib
import io
import json
import threading
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

from local_host.engine import HostError
from local_host.foreign_run import java_file_name, platform_key, run_source, status
from local_host.serve import LocalServer

TOKEN = "token-de-prueba"


def _server() -> tuple[LocalServer, str]:
    server = LocalServer(("127.0.0.1", 0), TOKEN, "http://127.0.0.1:9")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host = server.server_address[0]
    name = host.decode("ascii") if isinstance(host, bytes) else str(host)
    return server, f"http://{name}:{server.server_address[1]}"


def _call(origin: str, path: str, body: dict[str, object]) -> tuple[int, Any]:
    request = urllib.request.Request(
        f"{origin}{path}",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return response.status, json.loads(response.read().decode())


def _none(_name: str) -> str | None:
    return None


def _zip_script() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        info = zipfile.ZipInfo("tool/python")
        info.external_attr = 0o755 << 16
        info.create_system = 3
        archive.writestr(info, b"#!/bin/sh\necho cached\n")
    return buffer.getvalue()


def _manifest(payload: bytes, digest: str) -> dict[str, Any]:
    return {
        "runtimes": {
            "python": {
                "version": "1",
                "files": {
                    platform_key(): {
                        "url": "https://runtimes.example/python.zip",
                        "sha256": digest,
                        "archive": "zip",
                        "bins": {"python": "tool/python"},
                    }
                },
            }
        }
    }


def test_python_del_sistema_escribe_la_salida() -> None:
    server, origin = _server()
    try:
        code, body = _call(
            origin,
            "/local/v1/foreign/run",
            {"language": "python", "source": "print(6)\n", "stdin": ""},
        )
    finally:
        server.shutdown()
    assert code == 200
    assert body["status"] == "ok"
    assert body["stdout"] == "6\n"
    assert body["via"] == "system"


def test_sin_la_funcion_del_plan_no_corre() -> None:
    server, origin = _server()
    server.entitlements.remember_trusted({"features": {"languages": False, "execute": True}})
    try:
        try:
            _call(
                origin,
                "/local/v1/foreign/run",
                {"language": "python", "source": "print(6)\n", "stdin": ""},
            )
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
            return
        raise AssertionError("el plan apagado debía rechazar la corrida")
    finally:
        server.shutdown()


def test_un_lenguaje_ajeno_no_corre() -> None:
    try:
        run_source("ruby", "puts 1\n", manifest={})
    except HostError as exc:
        assert exc.message == "Ese lenguaje no está en la lista."
        return
    raise AssertionError("debía rechazar el lenguaje")


def test_c_no_descarga_aunque_el_manifiesto_tenga_url(tmp_path: Path) -> None:
    called = False

    def fetch(_url: str) -> bytes:
        nonlocal called
        called = True
        return b""

    payload = _zip_script()
    result = run_source(
        "c",
        "int main(void) { return 0; }\n",
        root=tmp_path,
        manifest=_manifest(payload, hashlib.sha256(payload).hexdigest()),
        finder=_none,
        fetch=fetch,
    )
    assert result["status"] == "missing"
    assert result["message"] == "Falta el runtime en esta máquina."
    assert called is False


def test_la_suma_incorrecta_no_instala(tmp_path: Path) -> None:
    payload = _zip_script()
    result = run_source(
        "python",
        "print(1)\n",
        root=tmp_path,
        manifest=_manifest(payload, "0" * 64),
        finder=_none,
        fetch=lambda _url: payload,
    )
    assert result["status"] == "error"
    assert result["message"] == "La suma del runtime no coincide."
    assert list(tmp_path.rglob("python")) == []


def test_descarga_el_runtime_y_lo_reutiliza(tmp_path: Path) -> None:
    payload = _zip_script()
    digest = hashlib.sha256(payload).hexdigest()
    calls = 0

    def fetch(_url: str) -> bytes:
        nonlocal calls
        calls += 1
        return payload

    manifest = _manifest(payload, digest)
    first = run_source(
        "python",
        "print(1)\n",
        root=tmp_path,
        manifest=manifest,
        finder=_none,
        fetch=fetch,
    )
    second = run_source(
        "python",
        "print(1)\n",
        root=tmp_path,
        manifest=manifest,
        finder=_none,
        fetch=fetch,
    )
    assert first["status"] == "ok"
    assert first["via"] == "cached"
    assert first["stdout"] == "cached\n"
    assert second["via"] == "cached"
    assert calls == 1


def test_el_estado_no_marca_listo_un_runtime_vacio(tmp_path: Path) -> None:
    found = status(root=tmp_path, manifest={"runtimes": {}}, finder=_none)
    rows = found["languages"]
    assert found["platform"] == platform_key()
    assert isinstance(rows, list)
    assert all(isinstance(item, dict) and item["ready"] is False for item in rows)


def test_el_nombre_de_la_clase_java_sale_del_fuente() -> None:
    assert java_file_name("public class Saludo { }\n") == "Saludo.java"
    assert java_file_name("class Interna { }\n") == "Interna.java"
