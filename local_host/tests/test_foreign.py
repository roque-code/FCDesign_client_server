"""El editor de otros lenguajes corre en la máquina y no toca el pseudocódigo."""

from __future__ import annotations

import errno
import hashlib
import io
import json
import os
import tarfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from local_host.engine import HostError
from local_host.foreign_run import (
    _compile_argv,
    _decode_output,
    _extract,
    _isolated_env,
    _spawn,
    _sweep_sessions,
    _take_run_slot,
    java_file_name,
    load_manifest,
    open_session,
    platform_key,
    run_source,
    status,
)
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


def test_python_se_detiene_para_leer_un_dato() -> None:
    server, origin = _server()
    session = ""
    try:
        code, opened = _call(
            origin,
            "/local/v1/foreign/open",
            {"language": "python", "source": 'print(input("Dato: "))\n'},
        )
        assert code == 200
        assert opened["status"] == "waiting"
        assert "Dato:" in opened["stdout"]
        session = opened["session"]
        code, finished = _call(
            origin,
            "/local/v1/foreign/input",
            {"session": session, "text": "7"},
        )
        assert code == 200
        assert finished["status"] == "ok"
        assert "7" in finished["stdout"]
        assert finished["session"] == ""
        session = ""
    finally:
        if session:
            _call(origin, "/local/v1/foreign/close", {"session": session})
        server.shutdown()


def _tar_gz(members: list[tarfile.TarInfo], payloads: list[bytes]) -> bytes:
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w:gz") as archive:
        for info, payload in zip(members, payloads, strict=True):
            archive.addfile(info, io.BytesIO(payload) if payload else None)
    return raw.getvalue()


def test_un_enlace_interno_no_invalida_el_runtime(tmp_path: Path) -> None:
    body = b"hola\n"
    real = tarfile.TarInfo("tool/bin/real")
    real.size = len(body)
    link = tarfile.TarInfo("tool/bin/node")
    link.type = tarfile.SYMTYPE
    link.linkname = "real"
    _extract(_tar_gz([real, link], [body, b""]), tmp_path / "out", "tar.gz")
    assert (tmp_path / "out" / "tool" / "bin" / "node").is_file()


def test_un_enlace_que_sale_de_la_carpeta_se_rechaza(tmp_path: Path) -> None:
    link = tarfile.TarInfo("tool/node")
    link.type = tarfile.SYMTYPE
    link.linkname = "/etc/passwd"
    try:
        _extract(_tar_gz([link], [b""]), tmp_path / "out", "tar.gz")
    except (ValueError, tarfile.FilterError):
        return
    raise AssertionError("un enlace externo debía rechazarse")


def test_zig_compila_con_su_subcomando() -> None:
    c_argv = _compile_argv("/opt/zig", "c", Path("programa"), Path("programa.c"))
    cpp_argv = _compile_argv("/opt/zig.exe", "cpp", Path("programa"), Path("programa.cpp"))
    gcc_argv = _compile_argv("/usr/bin/gcc", "c", Path("programa"), Path("programa.c"))
    assert c_argv[:3] == ["/opt/zig", "cc", "-std=c11"]
    assert cpp_argv[:3] == ["/opt/zig.exe", "c++", "-std=c++17"]
    assert gcc_argv[:2] == ["/usr/bin/gcc", "-std=c11"]


def test_sin_terminal_python_igual_escribe(monkeypatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("sin terminal")

    monkeypatch.setattr("local_host.foreign_run._start_pty", boom)
    opened = open_session("python", 'print("hola")\n', download=False, isolated=True)
    assert opened["status"] == "ok", opened
    assert opened["stdout"] == "hola\n"


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


def test_el_runtime_se_baja_a_disco(tmp_path: Path) -> None:
    payload = _zip_script()
    digest = hashlib.sha256(payload).hexdigest()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    host, port = server.server_address
    manifest = _manifest(payload, digest)
    files = manifest["runtimes"]["python"]["files"][platform_key()]
    files["url"] = f"http://{host}:{port}/python.zip"
    try:
        result = run_source(
            "python",
            "print(1)\n",
            root=tmp_path,
            manifest=manifest,
            finder=_none,
        )
    finally:
        server.shutdown()
    assert result["status"] == "ok", result
    assert result["stdout"] == "cached\n"


def test_sin_espacio_lo_dice(tmp_path: Path) -> None:
    payload = _zip_script()

    def fetch(_url: str) -> bytes:
        raise OSError(errno.ENOSPC, "No space left on device")

    result = run_source(
        "python",
        "print(1)\n",
        root=tmp_path,
        manifest=_manifest(payload, hashlib.sha256(payload).hexdigest()),
        finder=_none,
        fetch=fetch,
    )
    assert result["message"] == "No hay espacio en el disco para instalar el runtime."


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


def test_una_suma_sha512_tambien_instala(tmp_path: Path) -> None:
    payload = _zip_script()
    digest = hashlib.sha512(payload).hexdigest()
    manifest = _manifest(payload, "")
    manifest["runtimes"]["python"]["files"][platform_key()]["sha512"] = digest
    result = run_source(
        "python",
        "print(1)\n",
        root=tmp_path,
        manifest=manifest,
        finder=_none,
        fetch=lambda _url: payload,
    )
    assert result["status"] == "ok"
    assert result["via"] == "cached"


def test_sin_variable_el_manifiesto_sale_del_servidor(tmp_path: Path, monkeypatch: Any) -> None:
    import local_host.foreign_run as foreign_run

    monkeypatch.delenv("TRAZA_RUNTIME_MANIFEST", raising=False)
    monkeypatch.setenv("TRAZA_RUNTIME_DIR", str(tmp_path))
    monkeypatch.setattr(foreign_run, "_api_origin", "http://cuentas.test")
    asked: list[str] = []

    def fail(location: str) -> dict[str, Any]:
        asked.append(location)
        raise HostError("No se pudo leer el manifiesto.")

    monkeypatch.setattr(foreign_run, "_read_manifest", fail)
    found = load_manifest()
    assert asked == ["http://cuentas.test/runtimes/manifest.json"]
    assert found["runtimes"]["python"]["version"] == ""


def test_un_manifiesto_ausente_deja_el_vacio(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("TRAZA_RUNTIME_MANIFEST", str(tmp_path / "no-esta.json"))
    monkeypatch.setenv("TRAZA_RUNTIME_DIR", str(tmp_path))
    found = load_manifest()
    assert found["runtimes"]["python"]["version"] == ""


def test_la_salida_oculta_los_codigos_de_pantalla() -> None:
    raw = b"\x1b[?1h\x1b=\x1b[?1h\x1b=hola\n\x1b[?1h\x1b="
    assert _decode_output(raw) == "hola\n"


def test_csharp_arranca_sin_icu() -> None:
    env = _isolated_env("csharp", {"dotnet": "/tmp/dotnet"}, "cached")
    assert env["DOTNET_SYSTEM_GLOBALIZATION_INVARIANT"] == "1"
    assert env["DOTNET_NOLOGO"] == "1"


def test_el_nombre_de_la_clase_java_sale_del_fuente() -> None:
    assert java_file_name("public class Saludo { }\n") == "Saludo.java"
    assert java_file_name("class Interna { }\n") == "Interna.java"


def test_sin_cupo_no_arranca_otro_proceso() -> None:
    import local_host.foreign_run as foreign_run

    taken = 0
    try:
        while foreign_run._run_slots.acquire(blocking=False):
            taken += 1
        with pytest.raises(HostError) as caught:
            _take_run_slot()
        assert caught.value.status == 429
        assert caught.value.message == foreign_run.BUSY_MESSAGE
        result = _spawn(["true"], "", Path("."), os.environ.copy(), "system")
        assert result["status"] == "error"
        assert result["message"] == foreign_run.BUSY_MESSAGE
    finally:
        for _ in range(taken):
            foreign_run._run_slots.release()


def test_un_programa_vencido_se_cierra(monkeypatch: Any) -> None:
    import local_host.foreign_run as foreign_run

    session = "a" * 32
    closed: list[str] = []

    class Fake:
        deadline = time.monotonic() - 1
        started = time.monotonic() - 100

    Fake.session = session

    monkeypatch.setattr(foreign_run, "close_session", lambda item: closed.append(item))
    with foreign_run._sessions_guard:
        foreign_run._sessions[session] = Fake()  # type: ignore[assignment]
    try:
        _sweep_sessions()
        assert closed == [session]
    finally:
        with foreign_run._sessions_guard:
            foreign_run._sessions.pop(session, None)
