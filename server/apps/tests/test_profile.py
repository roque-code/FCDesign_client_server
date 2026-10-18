"""El usuario cambia su nombre, su foto y su contraseña."""

import base64

import pytest
from rest_framework.test import APIClient

from apps.tests.helpers import PASSWORD, register

pytestmark = pytest.mark.django_db

_JPEG = b"\xff\xd8\xff" + b"\x00" * 40


def _photo(kind: str = "image/jpeg", raw: bytes = _JPEG) -> str:
    return f"data:{kind};base64,{base64.b64encode(raw).decode('ascii')}"


def test_cambia_nombre_foto_y_contrasena():
    client = APIClient()
    created = register(client, email="perfil@ejemplo.test", display_name="Ana Perfil")
    assert created.status_code == 201, created.content
    assert created.json()["avatar"] is None

    renamed = client.patch(
        "/api/v1/auth/me/",
        {"display_name": "Ana Vista", "avatar": _photo()},
        format="json",
    )
    assert renamed.status_code == 200, renamed.content
    assert renamed.json()["display_name"] == "Ana Vista"
    assert renamed.json()["avatar"] == _photo()

    refused = client.patch("/api/v1/auth/me/", {"role": "teacher"}, format="json")
    assert refused.status_code == 400
    assert client.get("/api/v1/auth/me/").json()["role"] == "student"
    assert client.get("/api/v1/auth/me/").json()["display_name"] == "Ana Vista"

    blank = client.patch("/api/v1/auth/me/", {"display_name": "   "}, format="json")
    assert blank.status_code == 400

    rejected = client.patch(
        "/api/v1/auth/me/",
        {"avatar": _photo("image/svg+xml", b"<svg xmlns='http://www.w3.org/2000/svg'/>" * 2)},
        format="json",
    )
    assert rejected.status_code == 400
    assert client.get("/api/v1/auth/me/").json()["avatar"] == _photo()

    mismatch = client.patch(
        "/api/v1/auth/me/",
        {"current_password": "otra-clave", "password": "Otra-clave-48"},
        format="json",
    )
    assert mismatch.status_code == 400
    short = client.patch(
        "/api/v1/auth/me/",
        {"current_password": PASSWORD, "password": "123"},
        format="json",
    )
    assert short.status_code == 400

    changed = client.patch(
        "/api/v1/auth/me/",
        {
            "display_name": "Ana Vista",
            "avatar": None,
            "current_password": PASSWORD,
            "password": "Otra-clave-48",
        },
        format="json",
    )
    assert changed.status_code == 200, changed.content
    assert changed.json()["avatar"] is None
    assert client.get("/api/v1/auth/me/").status_code == 200

    client.logout()
    denied = client.post(
        "/api/v1/auth/login/",
        {"email": "perfil@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert denied.status_code == 400
    entered = client.post(
        "/api/v1/auth/login/",
        {"email": "perfil@ejemplo.test", "password": "Otra-clave-48"},
        format="json",
    )
    assert entered.status_code == 200, entered.content
    assert entered.json()["display_name"] == "Ana Vista"
