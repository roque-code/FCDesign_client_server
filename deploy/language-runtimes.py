"""Deja Node, Java y .NET dentro de la imagen. En marcha, el contenedor no tiene salida.

C, C++ y Python usan el compilador y el intérprete del sistema. Este paso solo
corre al construir la imagen, cuando la red todavía existe.
"""

from __future__ import annotations

import sys

from local_host.foreign_run import _cached_or_download, _fetch_url, load_manifest, runtime_root

BUNDLED = ("javascript", "java", "csharp")


def main() -> None:
    manifest = load_manifest()
    root = runtime_root()
    root.mkdir(parents=True, exist_ok=True)
    for language in BUNDLED:
        ready = _cached_or_download(
            language,
            download=True,
            root=root,
            manifest=manifest,
            fetch=_fetch_url,
        )
        if ready is None:
            raise SystemExit(f"No se instaló {language}.")
        print(language, ", ".join(f"{key}={path}" for key, path in sorted(ready.items())))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"No se pudieron instalar los runtimes: {exc}", file=sys.stderr)
        raise
