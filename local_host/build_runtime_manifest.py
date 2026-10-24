"""Genera el manifiesto que publica el servidor.

No guarda los runtimes en el repositorio. Escribe solo las direcciones y las
sumas. Uso:

    python3 -m local_host.build_runtime_manifest --output deploy/runtimes/manifest.json
    python3 -m local_host.build_runtime_manifest --output deploy/runtimes/manifest.json --install-local
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path
from typing import Any

from local_host.foreign_run import app_support, ssl_context
from local_host.runtime_catalog import (
    JAVA_QUERY,
    build_manifest,
    dotnet_files,
    java_file,
    node_files,
    python_files,
)

_NODE_CHANNEL = "v22."
_PYTHON_SERIES = "3.13."
_DOTNET_CHANNEL = "8.0"


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el manifiesto de runtimes.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--install-local",
        action="store_true",
        help="También lo copia a la carpeta de datos de esta máquina.",
    )
    args = parser.parse_args()
    payload = generate()
    _write(args.output, payload)
    print(f"Manifiesto escrito en {args.output}")
    if args.install_local:
        destination = app_support() / "runtimes.json"
        _write(destination, payload)
        print(f"Copia local en {destination}")


def generate() -> dict[str, Any]:
    python_tag, python_version, python_sums = _python()
    node_version, node_sums = _node()
    java_version, java_map = _java()
    dotnet_version, dotnet_published = _dotnet()
    return build_manifest(
        python_version=python_version,
        python_files_map=python_files(python_tag, python_version, python_sums),
        node_version=node_version.lstrip("v"),
        node_files_map=node_files(node_version, node_sums),
        java_version=java_version,
        java_files_map=java_map,
        dotnet_version=dotnet_version,
        dotnet_files_map=dotnet_files(dotnet_version, dotnet_published),
    )


def _python() -> tuple[str, str, dict[str, str]]:
    release = _json(
        "https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest"
    )
    tag = str(release["tag_name"])
    version = ""
    for asset in release["assets"]:
        name = str(asset["name"])
        if (
            name.startswith(f"cpython-{_PYTHON_SERIES}")
            and name.endswith("-install_only.tar.gz")
            and "stripped" not in name
        ):
            version = name.split("+", 1)[0].removeprefix("cpython-")
            break
    if not version:
        raise SystemExit("El release de Python no trae CPython 3.13 install_only.")
    text = _text(
        "https://github.com/astral-sh/python-build-standalone/releases/download/"
        f"{tag}/SHA256SUMS"
    )
    return tag, version, _sums(text)


def _node() -> tuple[str, dict[str, str]]:
    rows = _json("https://nodejs.org/dist/index.json")
    version = ""
    for row in rows:
        candidate = str(row.get("version", ""))
        if row.get("lts") and candidate.startswith(_NODE_CHANNEL):
            version = candidate
            break
    if not version:
        raise SystemExit("No hay un Node 22 LTS en el índice.")
    return version, _sums(_text(f"https://nodejs.org/dist/{version}/SHASUMS256.txt"))


def _java() -> tuple[str, dict[str, dict[str, Any]]]:
    version = ""
    files: dict[str, dict[str, Any]] = {}
    for platform, (system, arch) in JAVA_QUERY.items():
        url = (
            "https://api.adoptium.net/v3/assets/feature_releases/21/ga"
            f"?architecture={arch}&heap_size=normal&image_type=jdk&os={system}"
            "&page=0&page_size=1&project=jdk&vendor=eclipse"
        )
        rows = _json(url)
        if not rows:
            raise SystemExit(f"Temurin no publicó Java 21 para {platform}.")
        item = rows[0]
        release_name = str(item["release_name"])
        version = release_name.removeprefix("jdk-")
        package = item["binaries"][0]["package"]
        files[platform] = java_file(
            platform,
            release_name,
            str(package["name"]),
            str(package["link"]),
            str(package["checksum"]),
        )
    return version, files


def _dotnet() -> tuple[str, list[dict[str, str]]]:
    index = _json("https://builds.dotnet.microsoft.com/dotnet/release-metadata/releases-index.json")
    channel = ""
    for row in index["releases-index"]:
        if row.get("channel-version") == _DOTNET_CHANNEL:
            channel = str(row["releases.json"])
            break
    if not channel:
        raise SystemExit("No está el canal 8.0 de .NET.")
    releases = _json(channel)
    sdk = releases["releases"][0]["sdk"]
    published: list[dict[str, str]] = []
    for item in sdk["files"]:
        published.append(
            {
                "name": str(item["name"]),
                "rid": str(item.get("rid", "")),
                "url": str(item["url"]),
                "hash": str(item["hash"]),
            }
        )
    return str(sdk["version"]), published


def _sums(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        found[parts[-1].lstrip("*")] = parts[0].strip().lower()
    return found


def _json(url: str) -> Any:
    return json.loads(_text(url))


def _text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Aulivana-FCDdesign"})
    with urllib.request.urlopen(request, timeout=60, context=ssl_context()) as response:
        data = response.read()
    if not isinstance(data, bytes):
        raise SystemExit(f"La respuesta de {url} no es binaria.")
    return data.decode("utf-8")


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
