"""El navegador ejecuta un lenguaje en el servidor cuando el nivel lo permite."""

import pytest
from rest_framework.test import APIClient

from apps.billing.models import Plan
from apps.languages.bridge import dispatch
from apps.tests.helpers import refresh_csrf, register
from config.errors import DomainError

pytestmark = pytest.mark.django_db


def _browser() -> APIClient:
    client = APIClient(enforce_csrf_checks=True, HTTP_X_AULIVANA_FCDDESIGN_CLIENT="")
    refresh_csrf(client)
    return client


def _enable_languages() -> None:
    plan = Plan.objects.get(audience="student", code="premium")
    plan.features = {**plan.features, "languages": True}
    plan.save(update_fields=["features"])


def test_sin_la_opcion_el_navegador_no_ejecuta():
    client = _browser()
    created = register(client, email="lenguaje.cerrado@ejemplo.test")
    assert created.status_code == 201, created.content
    denied = client.post(
        "/api/v1/languages/open/",
        {"language": "python", "source": 'print("hola")\n'},
        format="json",
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "plan_forbidden"


def test_el_servidor_no_ejecuta_el_lenguaje_dentro_del_proceso(monkeypatch):
    monkeypatch.setenv("TRAZA_LANGUAGE_HOST", "0")
    monkeypatch.delenv("TRAZA_LANGUAGE_TOKEN", raising=False)
    with pytest.raises(DomainError) as raised:
        dispatch("run", {"language": "python", "source": 'print("hola")\n'})
    assert raised.value.code == "unavailable"
    assert raised.value.status_code == 503


def test_el_navegador_ejecuta_python_y_puede_enviar_un_dato():
    _enable_languages()
    client = _browser()
    created = register(client, email="lenguaje.navegador@ejemplo.test")
    assert created.status_code == 201, created.content

    opened = client.post(
        "/api/v1/languages/open/",
        {"language": "python", "source": 'print("hola")\n'},
        format="json",
    )
    assert opened.status_code == 200, opened.content
    body = opened.json()
    assert body["status"] == "ok"
    assert body["stdout"] == "hola\n"
    assert body["session"] == ""

    waiting = client.post(
        "/api/v1/languages/open/",
        {"language": "python", "source": "print(input())\n"},
        format="json",
    )
    assert waiting.status_code == 200, waiting.content
    live = waiting.json()
    assert live["status"] == "waiting"
    assert live["session"]
    fed = client.post(
        "/api/v1/languages/input/",
        {"session": live["session"], "text": "hola"},
        format="json",
    )
    assert fed.status_code == 200, fed.content
    assert fed.json()["status"] == "ok"
    assert fed.json()["stdout"].endswith("hola\n")
