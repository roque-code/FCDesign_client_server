"""El navegador ejecuta un lenguaje en el servidor cuando el nivel lo permite."""

import pytest
from rest_framework.test import APIClient

from apps.billing.models import Plan
from apps.tests.helpers import refresh_csrf, register

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
    from apps.languages.bridge import dispatch
    from config.errors import DomainError

    with pytest.raises(DomainError) as caught:
        dispatch("open", {"language": "python", "source": 'print(input())\n'})
    assert caught.value.code == "unavailable"
    assert caught.value.status_code == 503


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


def test_validar_marca_la_linea_y_no_gasta_ejecuciones():
    _enable_languages()
    client = _browser()
    created = register(client, email="lenguaje.validar@ejemplo.test")
    assert created.status_code == 201, created.content
    plan = Plan.objects.get(audience="student", code="premium")
    plan.max_executions_per_day = 1
    plan.save(update_fields=["max_executions_per_day"])

    ran = client.post(
        "/api/v1/languages/open/",
        {"language": "python", "source": 'print("hola")\n'},
        format="json",
    )
    assert ran.status_code == 200, ran.content
    broken = client.post(
        "/api/v1/languages/check/",
        {"language": "python", "source": 'x = 1\nprint("hola"\n'},
        format="json",
    )
    assert broken.status_code == 200, broken.content
    body = broken.json()
    assert body["status"] == "error"
    assert body["diagnostics"][0]["line"] == 2
    assert "SyntaxError" in body["diagnostics"][0]["message"]
    clean = client.post(
        "/api/v1/languages/check/",
        {"language": "python", "source": 'print("hola")\n'},
        format="json",
    )
    assert clean.status_code == 200, clean.content
    assert clean.json()["status"] == "ok"
    assert clean.json()["diagnostics"] == []
    assert client.get("/api/v1/auth/me/").json()["usage"]["executions_today"] == 1


def test_validar_tiene_un_tope_por_minuto():
    _enable_languages()
    client = _browser()
    created = register(client, email="lenguaje.tope@ejemplo.test")
    assert created.status_code == 201, created.content
    answers = [
        client.post(
            "/api/v1/languages/check/",
            {"language": "python", "source": 'print("hola")\n'},
            format="json",
        )
        for _ in range(4)
    ]
    assert [answer.status_code for answer in answers] == [200, 200, 200, 429]
    assert answers[-1].json()["error"]["code"] == "rate_limited"
