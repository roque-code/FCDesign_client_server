"""El administrador bloquea cuentas y ve quién sigue conectado."""

import time

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.tests.helpers import PASSWORD, refresh_csrf, register

pytestmark = pytest.mark.django_db


def _admin() -> APIClient:
    call_command("create_admin", email="admin-bloqueo@ejemplo.test", password=PASSWORD, name="Ada")
    admin = APIClient(enforce_csrf_checks=True)
    refresh_csrf(admin)
    entered = admin.post(
        "/api/v1/auth/login/",
        {"email": "admin-bloqueo@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert entered.status_code == 200, entered.content
    refresh_csrf(admin)
    return admin


def test_bloquear_cierra_la_sesion_y_el_tablero_la_quita(client):
    created = register(client, email="conectado@ejemplo.test", display_name="Luz")
    assert created.status_code == 201, created.content
    admin = _admin()
    live = admin.get("/api/v1/billing/sessions/")
    assert live.status_code == 200, live.content
    emails = [row["email"] for row in live.json()["results"]]
    assert "conectado@ejemplo.test" in emails
    row = next(item for item in live.json()["results"] if item["email"] == "conectado@ejemplo.test")
    assert row["display_name"] == "Luz"
    assert row["seconds"] >= 0
    assert row["started_at"]

    person = admin.get("/api/v1/billing/users/?q=conectado@ejemplo.test").json()["results"][0]
    assert person["blocked"] is False
    blocked = admin.patch(
        f"/api/v1/billing/users/{person['id']}/",
        {"blocked": True},
        format="json",
    )
    assert blocked.status_code == 200, blocked.content
    assert blocked.json()["blocked"] is True
    closed = client.get("/api/v1/auth/me/")
    assert closed.status_code == 403
    assert closed.json()["error"]["code"] == "not_authenticated"
    gone = admin.get("/api/v1/billing/sessions/").json()["results"]
    assert "conectado@ejemplo.test" not in [item["email"] for item in gone]

    wrong = APIClient(enforce_csrf_checks=True)
    refresh_csrf(wrong)
    missed = wrong.post(
        "/api/v1/auth/login/",
        {"email": "conectado@ejemplo.test", "password": "otra-clave"},
        format="json",
    )
    assert missed.status_code == 400
    assert missed.json()["error"]["message"] == "Correo o contraseña incorrectos."

    refused = APIClient(enforce_csrf_checks=True)
    refresh_csrf(refused)
    denied = refused.post(
        "/api/v1/auth/login/",
        {"email": "conectado@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "account_blocked"

    opened = admin.patch(
        f"/api/v1/billing/users/{person['id']}/",
        {"blocked": False},
        format="json",
    )
    assert opened.status_code == 200
    assert opened.json()["blocked"] is False
    refresh_csrf(refused)
    back = refused.post(
        "/api/v1/auth/login/",
        {"email": "conectado@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert back.status_code == 200, back.content


def test_el_tiempo_de_sesion_no_vuelve_a_cero(client):
    created = register(client, email="presente@ejemplo.test", display_name="Paz")
    assert created.status_code == 201, created.content
    started = int(time.time()) - 500
    session = client.session
    session["session_started"] = started
    session["last_activity"] = started
    session["last_seen"] = int(time.time())
    session.save()

    admin = _admin()
    listed = admin.get("/api/v1/billing/sessions/")
    assert listed.status_code == 200, listed.content
    row = next(item for item in listed.json()["results"] if item["email"] == "presente@ejemplo.test")
    assert row["seconds"] >= 500

    ping = client.get("/api/v1/auth/me/", HTTP_X_TRAZA_PRESENCE="1")
    assert ping.status_code == 200, ping.content
    assert client.session["session_started"] == started

    again = admin.get("/api/v1/billing/sessions/")
    kept = next(item for item in again.json()["results"] if item["email"] == "presente@ejemplo.test")
    assert kept["seconds"] >= 500

    session = client.session
    session["last_seen"] = int(time.time()) - 120
    session.save()
    gone = admin.get("/api/v1/billing/sessions/").json()["results"]
    assert "presente@ejemplo.test" not in [item["email"] for item in gone]


def test_un_alumno_no_ve_el_tablero_ni_bloquea(client):
    register(client, email="alumno-sesion@ejemplo.test", display_name="Ana")
    assert client.get("/api/v1/billing/sessions/").status_code == 403
    blocked = client.patch(
        "/api/v1/billing/users/1/",
        {"blocked": True},
        format="json",
    )
    assert blocked.status_code == 403
