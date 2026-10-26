"""Manifiesto vacío de runtimes.

La ventana no consulta la página de cada lenguaje al ejecutar. Las direcciones
y las sumas se publican con `python3 -m local_host.build_runtime_manifest`.
La aplicación las lee de TRAZA_RUNTIME_MANIFEST o de runtimes.json en la
carpeta de datos. C y C++ usan el cc de la máquina o el Zig publicado. Una
entrada sin url, o sin suma sha256 de 64 hexadecimales ni sha512 de 128,
no se descarga.
"""

from __future__ import annotations

from typing import Any

_PLATFORMS = (
    "darwin-arm64",
    "darwin-x86_64",
    "windows-x86_64",
    "windows-arm64",
    "linux-x86_64",
    "linux-arm64",
)


def _files(unix_bins: dict[str, str], windows_bins: dict[str, str]) -> dict[str, dict[str, Any]]:
    files: dict[str, dict[str, Any]] = {}
    for platform in _PLATFORMS:
        windows = platform.startswith("windows-")
        files[platform] = {
            "url": "",
            "sha256": "",
            "archive": "zip" if windows else "tar.gz",
            "bins": windows_bins if windows else unix_bins,
        }
    return files


DEFAULT_MANIFEST: dict[str, Any] = {
    "version": 1,
    "note": (
        "Publica aquí la versión, la dirección y la suma sha256 de cada archivo, "
        "para cada sistema. Python sale de un CPython reubicable, Node de nodejs.org, "
        "Java de Eclipse Temurin y C# del SDK de Microsoft. Esos archivos se guardan "
        "junto al paquete de escritorio. La aplicación los deja en su carpeta de datos."
    ),
    "runtimes": {
        "python": {
            "version": "",
            "files": _files(
                {"python": "python/bin/python3"},
                {"python": "python/python.exe"},
            ),
        },
        "node": {
            "version": "",
            "files": _files(
                {"node": "bin/node"},
                {"node": "node.exe"},
            ),
        },
        "java": {
            "version": "",
            "files": _files(
                {"java": "bin/java", "javac": "bin/javac"},
                {"java": "bin/java.exe", "javac": "bin/javac.exe"},
            ),
        },
        "dotnet": {
            "version": "",
            "files": _files(
                {"dotnet": "dotnet"},
                {"dotnet": "dotnet.exe"},
            ),
        },
    },
}
