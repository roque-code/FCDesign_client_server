"""Ejecuta código de otro lenguaje en esta máquina.

Primero busca el programa en el PATH. Si no está, y el manifiesto trae url y
suma para este sistema, descarga ese archivo a la carpeta de datos y lo usa.
C y C++ no se descargan: usan el cc de la máquina.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from local_host.engine import HostError
from local_host.runtime_manifest import DEFAULT_MANIFEST

MAX_SOURCE = 256 * 1024
MAX_STDIN = 64 * 1024
MAX_ARCHIVE = 450 * 1024 * 1024
MAX_OUTPUT = 100_000
RUN_TIMEOUT = 15
COMPILE_TIMEOUT = 30

LABELS: dict[str, str] = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "c": "C",
    "cpp": "C++",
    "csharp": "C#",
}

RUNTIME_OF: dict[str, str] = {
    "python": "python",
    "javascript": "node",
    "typescript": "node",
    "java": "java",
    "csharp": "dotnet",
}

SYSTEM: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "python": (("python", ("python3", "python")),),
    "javascript": (("node", ("node",)),),
    "typescript": (("node", ("node",)),),
    "java": (("javac", ("javac",)), ("java", ("java",))),
    "c": (("cc", ("cc",)),),
    "cpp": (("cxx", ("c++", "g++", "clang++")),),
    "csharp": (("dotnet", ("dotnet",)),),
}

NEEDED: dict[str, tuple[str, ...]] = {
    "python": ("python",),
    "javascript": ("node",),
    "typescript": ("node",),
    "java": ("javac", "java"),
    "csharp": ("dotnet",),
}

Finder = Callable[[str], str | None]
Fetch = Callable[[str], bytes]

_install_guard = threading.Lock()
_install_locks: dict[str, threading.Lock] = {}


class _RuntimeProblem(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class _Prepared:
    via: str
    commands: dict[str, str]


def platform_key() -> str:
    system = {"darwin": "darwin", "win32": "windows", "linux": "linux"}.get(
        sys.platform, sys.platform
    )
    machine = platform.machine().lower()
    arch = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }.get(machine, machine or "unknown")
    return f"{system}-{arch}"


def app_support() -> Path:
    override = os.environ.get("TRAZA_RUNTIME_DIR", "").strip()
    if override:
        return Path(override)
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Aulivana-FCDdesign"
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        base = Path(local) if local else home / "AppData" / "Local"
        return base / "Aulivana-FCDdesign"
    data = os.environ.get("XDG_DATA_HOME", "")
    base = Path(data) if data else home / ".local" / "share"
    return base / "Aulivana-FCDdesign"


def runtime_root() -> Path:
    return app_support() / "runtimes"


def load_manifest() -> dict[str, Any]:
    location = os.environ.get("TRAZA_RUNTIME_MANIFEST", "").strip()
    if location:
        return _read_manifest(location)
    local = app_support() / "runtimes.json"
    if local.is_file():
        return _read_manifest(str(local))
    return json.loads(json.dumps(DEFAULT_MANIFEST))


def status(
    *,
    root: Path | None = None,
    manifest: dict[str, Any] | None = None,
    finder: Finder | None = None,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for language in LABELS:
        prepared = _prepare(
            language,
            download=False,
            root=root or runtime_root(),
            manifest=manifest if manifest is not None else load_manifest(),
            finder=finder or shutil.which,
            fetch=_fetch_url,
        )
        rows.append(
            {
                "language": language,
                "label": LABELS[language],
                "ready": prepared is not None,
                "via": "missing" if prepared is None else prepared.via,
            }
        )
    return {"platform": platform_key(), "languages": rows}


def run_source(
    language: str,
    source: str,
    stdin: str = "",
    *,
    root: Path | None = None,
    manifest: dict[str, Any] | None = None,
    finder: Finder | None = None,
    fetch: Fetch | None = None,
) -> dict[str, object]:
    if language not in LABELS:
        raise HostError("Ese lenguaje no está en la lista.")
    if len(source) > MAX_SOURCE or len(stdin) > MAX_STDIN:
        raise HostError("El código es demasiado grande.")
    try:
        prepared = _prepare(
            language,
            download=True,
            root=root or runtime_root(),
            manifest=manifest if manifest is not None else load_manifest(),
            finder=finder or shutil.which,
            fetch=fetch or _fetch_url,
        )
    except _RuntimeProblem as exc:
        return _result("error", "missing", None, "", "", exc.message)
    if prepared is None:
        return _result("missing", "missing", None, "", "", "Falta el runtime en esta máquina.")
    if language == "typescript" and not _node_strips_types(prepared.commands["node"]):
        return _result(
            "error",
            prepared.via,
            None,
            "",
            "",
            "TypeScript necesita Node 22 o posterior.",
        )
    return _execute(language, source, stdin, prepared)


def java_file_name(source: str) -> str:
    public = _class_name(source, public=True)
    name = public or _class_name(source, public=False) or "Programa"
    return f"{name}.java"


def _prepare(
    language: str,
    *,
    download: bool,
    root: Path,
    manifest: dict[str, Any],
    finder: Finder,
    fetch: Fetch,
) -> _Prepared | None:
    system = _system_commands(language, finder)
    if system is not None:
        return _Prepared("system", system)
    cached = _cached_or_download(
        language, download=download, root=root, manifest=manifest, fetch=fetch
    )
    if cached is None:
        return None
    return _Prepared("cached", cached)


def _system_commands(language: str, finder: Finder) -> dict[str, str] | None:
    found: dict[str, str] = {}
    for key, names in SYSTEM[language]:
        path = _first(names, finder)
        if path is None:
            return None
        found[key] = path
    return found


def _first(names: tuple[str, ...], finder: Finder) -> str | None:
    for name in names:
        found = finder(name)
        if found:
            return found
    return None


def _cached_or_download(
    language: str,
    *,
    download: bool,
    root: Path,
    manifest: dict[str, Any],
    fetch: Fetch,
) -> dict[str, str] | None:
    runtime_id = RUNTIME_OF.get(language)
    if runtime_id is None:
        return None
    entry = _entry(manifest, runtime_id)
    if entry is None:
        return None
    folder = root / runtime_id / platform_key() / entry["version"]
    ready = _command_map(language, folder, entry["bins"], entry["sha256"])
    if ready is not None:
        return ready
    if not download or not _published(entry):
        return None
    lock = _install_lock(f"{runtime_id}:{platform_key()}:{entry['version']}")
    with lock:
        ready = _command_map(language, folder, entry["bins"], entry["sha256"])
        if ready is not None:
            return ready
        try:
            payload = fetch(entry["url"])
        except OSError as exc:
            raise _RuntimeProblem("No se pudo descargar el runtime.") from exc
        if not _matches(payload, entry["sha256"]):
            raise _RuntimeProblem("La suma del runtime no coincide.")
        try:
            _extract(payload, folder, entry["archive"])
        except (OSError, tarfile.TarError, zipfile.BadZipFile, ValueError) as exc:
            shutil.rmtree(folder, ignore_errors=True)
            raise _RuntimeProblem("El archivo del runtime no es válido.") from exc
        mapped = _command_map(language, folder, entry["bins"], "")
        if mapped is None:
            shutil.rmtree(folder, ignore_errors=True)
            raise _RuntimeProblem("El archivo del runtime no es válido.")
        for path in mapped.values():
            _mark_exec(Path(path))
        (folder / ".sha256").write_text(entry["sha256"].strip().lower() + "\n", encoding="utf-8")
        return mapped


def _entry(manifest: dict[str, Any], runtime_id: str) -> dict[str, Any] | None:
    runtimes = manifest.get("runtimes")
    if not isinstance(runtimes, dict):
        return None
    runtime = runtimes.get(runtime_id)
    if not isinstance(runtime, dict):
        return None
    version = runtime.get("version")
    files = runtime.get("files")
    if not isinstance(version, str) or not version.strip() or not isinstance(files, dict):
        return None
    raw = files.get(platform_key())
    if not isinstance(raw, dict):
        return None
    bins = raw.get("bins")
    archive = raw.get("archive")
    url = raw.get("url")
    sha = raw.get("sha256")
    if not isinstance(bins, dict) or not isinstance(archive, str):
        return None
    return {
        "version": version.strip(),
        "url": url if isinstance(url, str) else "",
        "sha256": sha if isinstance(sha, str) else "",
        "archive": archive,
        "bins": bins,
    }


def _published(entry: dict[str, Any]) -> bool:
    url = entry["url"]
    sha = entry["sha256"].strip().lower()
    return (
        isinstance(url, str)
        and url.startswith(("https://", "http://"))
        and len(sha) == 64
        and all(ch in "0123456789abcdef" for ch in sha)
    )


def _command_map(
    language: str, folder: Path, bins: dict[str, Any], sha: str
) -> dict[str, str] | None:
    if sha:
        stamp = folder / ".sha256"
        if not stamp.is_file() or stamp.read_text(encoding="utf-8").strip() != sha.strip().lower():
            return None
    commands: dict[str, str] = {}
    for key in NEEDED[language]:
        relative = bins.get(key)
        if not isinstance(relative, str) or not relative:
            return None
        path = _bin_path(folder, relative)
        if path is None:
            return None
        commands[key] = str(path)
    return commands


def _bin_path(folder: Path, relative: str) -> Path | None:
    path = folder / relative
    if path.is_file():
        return path
    if os.name == "nt" and not relative.endswith(".exe"):
        exe = folder / f"{relative}.exe"
        if exe.is_file():
            return exe
    return None


def _extract(payload: bytes, folder: Path, archive: str) -> None:
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    if archive == "zip":
        _extract_zip(payload, folder)
        return
    if archive in {"tar.gz", "tar.xz", "tar.bz2", "tar"}:
        _extract_tar(payload, folder)
        return
    raise ValueError(archive)


def _extract_zip(payload: bytes, folder: Path) -> None:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        for info in archive.infolist():
            _safe_name(info.filename)
        archive.extractall(folder)


def _extract_tar(payload: bytes, folder: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
        for member in archive.getmembers():
            _safe_name(member.name)
            if member.issym() or member.islnk():
                raise ValueError(member.name)
        archive.extractall(folder, filter="data")


def _safe_name(name: str) -> None:
    if not name or name.startswith(("/", "\\")):
        raise ValueError(name)
    if ".." in Path(name).parts:
        raise ValueError(name)


def _matches(payload: bytes, expected: str) -> bool:
    digest = hashlib.sha256(payload).hexdigest()
    wanted = expected.strip().lower()
    if len(digest) != len(wanted):
        return False
    return hmac.compare_digest(digest, wanted)


def _mark_exec(path: Path) -> None:
    if os.name == "nt" or not path.is_file():
        return
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _install_lock(key: str) -> threading.Lock:
    with _install_guard:
        lock = _install_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _install_locks[key] = lock
        return lock


def _execute(language: str, source: str, stdin: str, prepared: _Prepared) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="traza-foreign-") as folder_name:
        folder = Path(folder_name)
        env = _child_env(language, prepared.commands, prepared.via)
        if language == "python":
            path = folder / "programa.py"
            path.write_text(source, encoding="utf-8")
            return _spawn(
                [prepared.commands["python"], str(path)], stdin, folder, env, prepared.via
            )
        if language == "javascript":
            path = folder / "programa.js"
            path.write_text(source, encoding="utf-8")
            return _spawn([prepared.commands["node"], str(path)], stdin, folder, env, prepared.via)
        if language == "typescript":
            path = folder / "programa.ts"
            path.write_text(source, encoding="utf-8")
            return _spawn(
                [prepared.commands["node"], "--experimental-strip-types", str(path)],
                stdin,
                folder,
                env,
                prepared.via,
            )
        if language == "java":
            return _run_java(source, stdin, folder, env, prepared)
        if language == "c":
            return _run_native(
                source,
                stdin,
                folder,
                env,
                prepared,
                "programa.c",
                [prepared.commands["cc"], "-std=c11", "-o"],
            )
        if language == "cpp":
            return _run_native(
                source,
                stdin,
                folder,
                env,
                prepared,
                "programa.cpp",
                [prepared.commands["cxx"], "-std=c++17", "-o"],
            )
        return _run_csharp(source, stdin, folder, env, prepared)


def _run_java(
    source: str, stdin: str, folder: Path, env: dict[str, str], prepared: _Prepared
) -> dict[str, object]:
    name = java_file_name(source)
    (folder / name).write_text(source, encoding="utf-8")
    compiled = _spawn(
        [prepared.commands["javac"], name],
        "",
        folder,
        env,
        prepared.via,
        timeout=COMPILE_TIMEOUT,
    )
    if compiled["status"] != "ok":
        return compiled
    return _spawn(
        [prepared.commands["java"], "-cp", str(folder), Path(name).stem],
        stdin,
        folder,
        env,
        prepared.via,
    )


def _run_native(
    source: str,
    stdin: str,
    folder: Path,
    env: dict[str, str],
    prepared: _Prepared,
    filename: str,
    compiler: list[str],
) -> dict[str, object]:
    binary = folder / ("programa.exe" if os.name == "nt" else "programa")
    (folder / filename).write_text(source, encoding="utf-8")
    compiled = _spawn(
        [*compiler, str(binary), str(folder / filename), "-lm"],
        "",
        folder,
        env,
        prepared.via,
        timeout=COMPILE_TIMEOUT,
    )
    if compiled["status"] != "ok":
        return compiled
    return _spawn([str(binary)], stdin, folder, env, prepared.via)


def _run_csharp(
    source: str, stdin: str, folder: Path, env: dict[str, str], prepared: _Prepared
) -> dict[str, object]:
    framework = _dotnet_tfm(prepared.commands["dotnet"])
    project = (
        '<Project Sdk="Microsoft.NET.Sdk">\n'
        "  <PropertyGroup>\n"
        "    <OutputType>Exe</OutputType>\n"
        f"    <TargetFramework>{framework}</TargetFramework>\n"
        "    <ImplicitUsings>enable</ImplicitUsings>\n"
        "    <Nullable>disable</Nullable>\n"
        "  </PropertyGroup>\n"
        "</Project>\n"
    )
    (folder / "Programa.csproj").write_text(project, encoding="utf-8")
    (folder / "Programa.cs").write_text(source, encoding="utf-8")
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    return _spawn(
        [prepared.commands["dotnet"], "run", "--project", str(folder), "--nologo"],
        stdin,
        folder,
        env,
        prepared.via,
        timeout=60,
    )


def _dotnet_tfm(dotnet: str) -> str:
    try:
        completed = subprocess.run(
            [dotnet, "--list-sdks"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "net8.0"
    versions = [
        line.split(" ", 1)[0] for line in completed.stdout.splitlines() if line[:1].isdigit()
    ]
    if not versions:
        return "net8.0"
    major = versions[-1].split(".", 1)[0]
    if not major.isdigit():
        return "net8.0"
    return f"net{major}.0"


def _node_strips_types(node: str) -> bool:
    try:
        completed = subprocess.run(
            [node, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    text = completed.stdout.strip().lstrip("v")
    parts = text.split(".")
    if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return False
    return (int(parts[0]), int(parts[1])) >= (22, 6)


def _child_env(language: str, commands: dict[str, str], via: str) -> dict[str, str]:
    env = os.environ.copy()
    if via != "cached":
        return env
    folders: list[str] = []
    for path in commands.values():
        folder = str(Path(path).parent)
        if folder not in folders:
            folders.append(folder)
    env["PATH"] = os.pathsep.join([*folders, env.get("PATH", "")])
    if language == "java":
        java = Path(commands["java"])
        if java.parent.name == "bin":
            env["JAVA_HOME"] = str(java.parent.parent)
    if language == "csharp":
        env["DOTNET_ROOT"] = str(Path(commands["dotnet"]).parent)
        env["DOTNET_MULTILEVEL_LOOKUP"] = "0"
    return env


def _spawn(
    argv: list[str],
    stdin: str,
    cwd: Path,
    env: dict[str, str],
    via: str,
    timeout: int = RUN_TIMEOUT,
) -> dict[str, object]:
    try:
        completed = subprocess.run(
            argv,
            input=stdin,
            text=True,
            capture_output=True,
            cwd=cwd,
            env=env,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return _result(
            "error", via, 124, stdout, stderr, "El programa superó el tiempo de ejecución."
        )
    except OSError:
        return _result("error", via, None, "", "", "No se pudo ejecutar.")
    state = "ok" if completed.returncode == 0 else "error"
    return _result(state, via, completed.returncode, completed.stdout, completed.stderr, "")


def _result(
    state: str,
    via: str,
    exit_code: int | None,
    stdout: str,
    stderr: str,
    message: str,
) -> dict[str, object]:
    return {
        "status": state,
        "via": via,
        "exit_code": exit_code,
        "stdout": _cap(stdout),
        "stderr": _cap(stderr),
        "message": message,
    }


def _cap(text: str) -> str:
    if len(text) <= MAX_OUTPUT:
        return text
    return text[:MAX_OUTPUT] + "\n…"


def _class_name(source: str, *, public: bool) -> str | None:
    pattern = (
        r"\bpublic\s+class\s+([A-Za-z_][A-Za-z0-9_]*)"
        if public
        else r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)"
    )
    found = re.search(pattern, source)
    if found is None:
        return None
    return found.group(1)


def _read_manifest(location: str) -> dict[str, Any]:
    try:
        if location.startswith(("https://", "http://")):
            payload = json.loads(_fetch_url(location).decode("utf-8"))
        else:
            payload = json.loads(Path(location).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise HostError("No se pudo leer el manifiesto.") from exc
    if not isinstance(payload, dict):
        raise HostError("No se pudo leer el manifiesto.")
    return payload


def _fetch_url(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Aulivana-FCDdesign"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return _read_limited(response)


def _read_limited(response: Any) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        block = response.read(1024 * 1024)
        if not block:
            break
        if not isinstance(block, bytes):
            raise OSError("La descarga no es binaria.")
        total += len(block)
        if total > MAX_ARCHIVE:
            raise OSError("El runtime supera el tamaño admitido.")
        chunks.append(block)
    return b"".join(chunks)
