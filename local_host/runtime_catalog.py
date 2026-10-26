"""Arma el manifiesto de runtimes a partir de datos ya resueltos.

No descarga nada. Las direcciones apuntan a los archivos oficiales y la suma
queda fija: la aplicación no busca una versión más nueva al ejecutar.
C y C++ usan el cc de la máquina; si no hay, el manifiesto publica Zig.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

PLATFORMS = (
    "darwin-arm64",
    "darwin-x86_64",
    "windows-x86_64",
    "windows-arm64",
    "linux-x86_64",
    "linux-arm64",
)

PYTHON_TRIPLE = {
    "darwin-arm64": "aarch64-apple-darwin",
    "darwin-x86_64": "x86_64-apple-darwin",
    "windows-x86_64": "x86_64-pc-windows-msvc",
    "windows-arm64": "aarch64-pc-windows-msvc",
    "linux-x86_64": "x86_64-unknown-linux-gnu",
    "linux-arm64": "aarch64-unknown-linux-gnu",
}

NODE_DIST = {
    "darwin-arm64": "darwin-arm64",
    "darwin-x86_64": "darwin-x64",
    "windows-x86_64": "win-x64",
    "windows-arm64": "win-arm64",
    "linux-x86_64": "linux-x64",
    "linux-arm64": "linux-arm64",
}

JAVA_QUERY = {
    "darwin-arm64": ("mac", "aarch64"),
    "darwin-x86_64": ("mac", "x64"),
    "windows-x86_64": ("windows", "x64"),
    "windows-arm64": ("windows", "aarch64"),
    "linux-x86_64": ("linux", "x64"),
    "linux-arm64": ("linux", "aarch64"),
}

ZIG_TARGET = {
    "darwin-arm64": "aarch64-macos",
    "darwin-x86_64": "x86_64-macos",
    "windows-x86_64": "x86_64-windows",
    "windows-arm64": "aarch64-windows",
    "linux-x86_64": "x86_64-linux",
    "linux-arm64": "aarch64-linux",
}

DOTNET_RID = {
    "darwin-arm64": "osx-arm64",
    "darwin-x86_64": "osx-x64",
    "windows-x86_64": "win-x64",
    "windows-arm64": "win-arm64",
    "linux-x86_64": "linux-x64",
    "linux-arm64": "linux-arm64",
}


def archive_of(name: str) -> str:
    if name.endswith(".zip"):
        return "zip"
    if name.endswith(".tar.gz"):
        return "tar.gz"
    if name.endswith(".tar.xz"):
        return "tar.xz"
    raise ValueError(name)


def python_files(tag: str, version: str, sums: dict[str, str]) -> dict[str, dict[str, Any]]:
    files: dict[str, dict[str, Any]] = {}
    for platform, triple in PYTHON_TRIPLE.items():
        name = f"cpython-{version}+{tag}-{triple}-install_only.tar.gz"
        digest = sums.get(name)
        if not digest:
            raise ValueError(f"Falta la suma de {name}.")
        windows = platform.startswith("windows-")
        files[platform] = {
            "url": (
                "https://github.com/astral-sh/python-build-standalone/releases/download/"
                f"{quote(tag)}/{quote(name)}"
            ),
            "sha256": digest,
            "archive": "tar.gz",
            "bins": {"python": "python/python.exe" if windows else "python/bin/python3"},
        }
    return files


def node_files(version: str, sums: dict[str, str]) -> dict[str, dict[str, Any]]:
    """version incluye la v, como v22.23.4."""
    files: dict[str, dict[str, Any]] = {}
    for platform, dist in NODE_DIST.items():
        windows = platform.startswith("windows-")
        suffix = "zip" if windows else "tar.gz"
        name = f"node-{version}-{dist}.{suffix}"
        digest = sums.get(name)
        if not digest:
            raise ValueError(f"Falta la suma de {name}.")
        folder = name[: -len(suffix) - 1]
        binary = f"{folder}/node.exe" if windows else f"{folder}/bin/node"
        files[platform] = {
            "url": f"https://nodejs.org/dist/{version}/{name}",
            "sha256": digest,
            "archive": archive_of(name),
            "bins": {"node": binary},
        }
    return files


def java_bins(platform: str, release_name: str) -> dict[str, str]:
    if platform.startswith("windows-"):
        base = f"{release_name}/bin"
        return {"java": f"{base}/java.exe", "javac": f"{base}/javac.exe"}
    if platform.startswith("darwin-"):
        base = f"{release_name}/Contents/Home/bin"
        return {"java": f"{base}/java", "javac": f"{base}/javac"}
    base = f"{release_name}/bin"
    return {"java": f"{base}/java", "javac": f"{base}/javac"}


def java_file(platform: str, release_name: str, name: str, url: str, sha256: str) -> dict[str, Any]:
    return {
        "url": url,
        "sha256": sha256,
        "archive": archive_of(name),
        "bins": java_bins(platform, release_name),
    }


def dotnet_files(version: str, published: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    """published trae rid, url, name y hash. El hash de Microsoft es sha512."""
    by_rid: dict[str, dict[str, str]] = {}
    for item in published:
        name = item["name"]
        if name.endswith(".pkg"):
            continue
        if not name.endswith((".tar.gz", ".zip")):
            continue
        rid = item["rid"]
        current = by_rid.get(rid)
        if current is None or (current["name"].endswith(".zip") and name.endswith(".tar.gz")):
            by_rid[rid] = item
    files: dict[str, dict[str, Any]] = {}
    for platform, rid in DOTNET_RID.items():
        item = by_rid.get(rid)
        if item is None:
            raise ValueError(f"Falta el SDK de .NET para {rid}.")
        windows = platform.startswith("windows-")
        files[platform] = {
            "url": item["url"],
            "sha256": "",
            "sha512": item["hash"].strip().lower(),
            "archive": archive_of(item["name"]),
            "bins": {"dotnet": "dotnet.exe" if windows else "dotnet"},
        }
    return files


def zig_files(version: str, sums: dict[str, str]) -> dict[str, dict[str, Any]]:
    files: dict[str, dict[str, Any]] = {}
    for platform, target in ZIG_TARGET.items():
        windows = platform.startswith("windows-")
        suffix = "zip" if windows else "tar.xz"
        name = f"zig-{target}-{version}.{suffix}"
        digest = sums.get(platform, "")
        if not digest:
            raise ValueError(f"Falta la suma de {name}.")
        folder = name[: -len(suffix) - 1]
        binary = f"{folder}/zig.exe" if windows else f"{folder}/zig"
        files[platform] = {
            "url": f"https://ziglang.org/download/{version}/{name}",
            "sha256": digest,
            "archive": archive_of(name),
            "bins": {"cc": binary, "cxx": binary},
        }
    return files


def build_manifest(
    *,
    python_version: str,
    python_files_map: dict[str, dict[str, Any]],
    node_version: str,
    node_files_map: dict[str, dict[str, Any]],
    java_version: str,
    java_files_map: dict[str, dict[str, Any]],
    dotnet_version: str,
    dotnet_files_map: dict[str, dict[str, Any]],
    zig_version: str,
    zig_files_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "version": 1,
        "note": (
            "Manifiesto fijo. Python es un CPython reubicable, Node sale de nodejs.org, "
            "Java de Eclipse Temurin 21 y C# del SDK 8 de Microsoft. "
            "C y C++ usan Zig si la máquina no tiene compilador. "
            "La aplicación guarda cada archivo en su carpeta de datos, no dentro del paquete."
        ),
        "runtimes": {
            "python": {"version": python_version, "files": python_files_map},
            "node": {"version": node_version, "files": node_files_map},
            "java": {"version": java_version, "files": java_files_map},
            "dotnet": {"version": dotnet_version, "files": dotnet_files_map},
            "zig": {"version": zig_version, "files": zig_files_map},
        },
    }
