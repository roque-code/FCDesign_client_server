"""Congela language_core con el CPython de esta máquina.

El binario queda con el triple de Rust para que Tauri lo encuentre al empaquetar.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "desktop" / "src-tauri"
BINARIES = DESKTOP / "binaries"


def triple() -> str:
    env = os.environ.get("TRAZA_TARGET_TRIPLE", "")
    if env:
        return env
    probe = subprocess.run(
        ["rustc", "-vV"],
        check=True,
        capture_output=True,
        text=True,
    )
    for line in probe.stdout.splitlines():
        if line.startswith("host: "):
            return line.split(": ", 1)[1].strip()
    raise SystemExit("rustc no dijo el triple de esta máquina.")


def main() -> None:
    name = triple()
    suffix = ".exe" if name.endswith("windows-msvc") else ""
    BINARIES.mkdir(parents=True, exist_ok=True)
    work = DESKTOP / "target" / "pyinstaller"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--name",
            "traza-host",
            "--paths",
            str(ROOT),
            "--distpath",
            str(work / "dist"),
            "--workpath",
            str(work / "work"),
            "--specpath",
            str(work),
            "--collect-submodules",
            "language_core",
            "--collect-submodules",
            "local_host",
            str(ROOT / "local_host" / "__main__.py"),
        ],
        cwd=ROOT,
        check=True,
    )
    built = work / "dist" / f"traza-host{suffix}"
    target = BINARIES / f"traza-host-{name}{suffix}"
    # macOS mata un ejecutable sobrescrito en el mismo archivo: la firma en caché ya no coincide.
    target.unlink(missing_ok=True)
    shutil.copy2(built, target)
    target.chmod(0o755)
    print(target)


if __name__ == "__main__":
    main()
