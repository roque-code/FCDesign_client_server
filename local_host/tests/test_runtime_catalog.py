"""El manifiesto fija direcciones y sumas. No consulta la red al armarse."""

from __future__ import annotations

from local_host.runtime_catalog import (
    PLATFORMS,
    build_manifest,
    dotnet_files,
    java_bins,
    java_file,
    node_files,
    python_files,
)


def test_python_apunta_al_archivo_reubicable() -> None:
    sums = {
        "cpython-3.13.17+20261021-aarch64-apple-darwin-install_only.tar.gz": "ab" * 32,
    }
    try:
        python_files("20261021", "3.13.17", sums)
    except ValueError as exc:
        assert "x86_64-apple-darwin" in str(exc)
        return
    raise AssertionError("debía faltar el resto de sistemas")


def test_python_de_mac_arm_usa_el_binario_reubicable() -> None:
    name = "cpython-3.13.17+20261021-aarch64-apple-darwin-install_only.tar.gz"
    sums = {
        f"cpython-3.13.17+20261021-{triple}-install_only.tar.gz": "cd" * 32
        for triple in (
            "aarch64-apple-darwin",
            "x86_64-apple-darwin",
            "x86_64-pc-windows-msvc",
            "aarch64-pc-windows-msvc",
            "x86_64-unknown-linux-gnu",
            "aarch64-unknown-linux-gnu",
        )
    }
    files = python_files("20261021", "3.13.17", sums)
    mac = files["darwin-arm64"]
    assert mac["bins"] == {"python": "python/bin/python3"}
    assert mac["sha256"] == "cd" * 32
    assert name.split("+")[0] in mac["url"] or "cpython-3.13.17" in mac["url"]
    assert "%2B" in mac["url"]
    assert files["windows-x86_64"]["bins"] == {"python": "python/python.exe"}
    assert set(files) == set(PLATFORMS)


def test_node_guarda_la_carpeta_del_archivo() -> None:
    sums = {}
    names = {
        "darwin-arm64": "node-v22.23.4-darwin-arm64.tar.gz",
        "darwin-x86_64": "node-v22.23.4-darwin-x64.tar.gz",
        "windows-x86_64": "node-v22.23.4-win-x64.zip",
        "windows-arm64": "node-v22.23.4-win-arm64.zip",
        "linux-x86_64": "node-v22.23.4-linux-x64.tar.gz",
        "linux-arm64": "node-v22.23.4-linux-arm64.tar.gz",
    }
    for name in names.values():
        sums[name] = "ef" * 32
    files = node_files("v22.23.4", sums)
    assert files["darwin-arm64"]["bins"] == {"node": "node-v22.23.4-darwin-arm64/bin/node"}
    assert files["windows-x86_64"]["archive"] == "zip"
    assert files["windows-x86_64"]["bins"] == {"node": "node-v22.23.4-win-x64/node.exe"}
    assert files["linux-arm64"]["url"].endswith(names["linux-arm64"])


def test_java_de_mac_entra_en_el_bundle() -> None:
    assert java_bins("darwin-arm64", "jdk-21.0.13+9")["javac"].endswith(
        "jdk-21.0.13+9/Contents/Home/bin/javac"
    )
    assert java_bins("linux-x86_64", "jdk-21.0.13+9")["java"].endswith("jdk-21.0.13+9/bin/java")
    packed = java_file(
        "windows-x86_64",
        "jdk-21.0.13+9",
        "OpenJDK21U-jdk_x64_windows_hotspot_21.0.13_9.zip",
        "https://example.test/jdk.zip",
        "aa" * 32,
    )
    assert packed["archive"] == "zip"
    assert packed["bins"]["java"].endswith("java.exe")


def test_dotnet_prefiere_el_tar_y_guarda_sha512() -> None:
    published = [
        {
            "name": "dotnet-sdk-osx-arm64.pkg",
            "rid": "osx-arm64",
            "url": "https://example.test/sdk.pkg",
            "hash": "11" * 64,
        },
        {
            "name": "dotnet-sdk-osx-arm64.tar.gz",
            "rid": "osx-arm64",
            "url": "https://example.test/sdk.tar.gz",
            "hash": "22" * 64,
        },
    ]
    for rid, name in (
        ("osx-x64", "dotnet-sdk-osx-x64.tar.gz"),
        ("win-x64", "dotnet-sdk-win-x64.zip"),
        ("win-arm64", "dotnet-sdk-win-arm64.zip"),
        ("linux-x64", "dotnet-sdk-linux-x64.tar.gz"),
        ("linux-arm64", "dotnet-sdk-linux-arm64.tar.gz"),
    ):
        published.append(
            {"name": name, "rid": rid, "url": f"https://example.test/{name}", "hash": "33" * 64}
        )
    files = dotnet_files("8.0.426", published)
    assert files["darwin-arm64"]["url"].endswith("sdk.tar.gz")
    assert files["darwin-arm64"]["sha512"] == "22" * 64
    assert files["darwin-arm64"]["sha256"] == ""
    assert files["windows-x86_64"]["bins"] == {"dotnet": "dotnet.exe"}
    assert files["linux-x86_64"]["bins"] == {"dotnet": "dotnet"}


def test_el_manifiesto_no_incluye_c() -> None:
    empty = {platform: {} for platform in PLATFORMS}
    payload = build_manifest(
        python_version="3.13.17",
        python_files_map=empty,
        node_version="22.23.4",
        node_files_map=empty,
        java_version="21.0.13+9",
        java_files_map=empty,
        dotnet_version="8.0.426",
        dotnet_files_map=empty,
    )
    assert set(payload["runtimes"]) == {"python", "node", "java", "dotnet"}
    assert "C y C++ no se descargan" in payload["note"]
