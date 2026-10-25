"""API de cuentas, proyectos, versiones y ejecución en proceso."""

import time
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.executions.live import peek
from apps.executions.models import Execution, ExecutionEvent
from apps.executions.runner import run_in_process
from apps.language.models import LanguageProfile
from apps.projects.examples import EXAMPLES
from apps.projects.models import AlgorithmVersion
from apps.tests.helpers import PASSWORD, refresh_csrf, register
from config.errors import DomainError
from language_core.grammar import STRICT

MISSING_END = """Algoritmo Roto
    Si 1 = 1 Entonces
        Escribir "hola";
FinAlgoritmo
"""

RUNTIME_ERROR = """Algoritmo Falla
    Definir n Como Entero;
    Escribir "antes";
    Escribir n;
FinAlgoritmo
"""

READ_NUMBER = """Algoritmo Lee
    Definir n Como Entero;
    Leer n;
    Escribir n;
FinAlgoritmo
"""


def _project_id(client):
    return client.get("/api/v1/projects/").json()["results"][0]["id"]


def _algorithm(client, name):
    rows = client.get("/api/v1/algorithms/?page_size=100").json()["results"]
    return next(row for row in rows if row["name"] == name)


def _execute(client, algorithm_id):
    """Ejecutar deja la sesión en pausa; Continuar la lleva hasta el final."""
    started = client.post(f"/api/v1/algorithms/{algorithm_id}/execute/")
    if started.status_code != 201 or started.json().get("status") != "paused":
        return started
    return client.post(
        f"/api/v1/executions/{started.json()['id']}/control/",
        {"action": "continue"},
        format="json",
    )


def test_register_login_logout_and_examples(client):
    created = register(client, display_name="Ana")
    assert created.status_code == 201
    assert created.json()["display_name"] == "Ana"
    assert len(client.get("/api/v1/algorithms/?page_size=100").json()["results"]) == 13
    assert client.get("/api/v1/meta/").json()["notice"].startswith("La ejecución ocurre")
    assert "Algoritmo" in client.get("/api/v1/language/keywords/").json()["keywords"]
    assert (
        "default-src 'self'" in client.get("/api/v1/auth/csrf/").headers["Content-Security-Policy"]
    )

    logged_out = client.post("/api/v1/auth/logout/")
    me = client.get("/api/v1/auth/me/")
    assert logged_out.status_code == 204, logged_out.content
    assert me.status_code == 403
    assert me.json()["error"]["code"] == "not_authenticated"
    refresh_csrf(client)
    logged = client.post(
        "/api/v1/auth/login/",
        {"email": "ana@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    refresh_csrf(client)
    assert logged.status_code == 200
    assert AuditEvent.objects.filter(action="auth.login").exists()


def test_password_reset_uses_the_memory_mailbox(client):
    register(client)
    asked = client.post(
        "/api/v1/auth/password-reset/", {"email": "ana@ejemplo.test"}, format="json"
    )
    assert asked.status_code == 200
    assert len(mail.outbox) == 1
    unknown = client.post(
        "/api/v1/auth/password-reset/", {"email": "nadie@ejemplo.test"}, format="json"
    )
    assert unknown.status_code == 200
    assert len(mail.outbox) == 1
    lines = dict(line.split("=", 1) for line in mail.outbox[0].body.splitlines())
    confirm = client.post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": lines["uid"], "token": lines["token"], "password": "Otra-clave-2"},
        format="json",
    )
    assert confirm.status_code == 200
    refresh_csrf(client)
    again = client.post(
        "/api/v1/auth/login/",
        {"email": "ana@ejemplo.test", "password": "Otra-clave-2"},
        format="json",
    )
    assert again.status_code == 200
    refresh_csrf(client)
    bad = client.post(
        "/api/v1/auth/password-reset/confirm/",
        {"uid": lines["uid"], "token": "no-sirve", "password": "Otra-clave-3"},
        format="json",
    )
    assert bad.status_code == 400


def _confirmation_query() -> dict[str, list[str]]:
    link = next(line for line in mail.outbox[-1].body.splitlines() if line.startswith("http"))
    return parse_qs(urlparse(link).query)


@override_settings(
    EMAIL_CONFIRMATION_REQUIRED=True,
    TRAZA_PUBLIC_ORIGIN="http://127.0.0.1:18080",
    TRAZA_MAIL_UI="http://127.0.0.1:8025",
)
def test_register_sends_confirmation_before_login(client):
    created = register(client, email="nuevo@ejemplo.test", display_name="Nuevo")
    assert created.status_code == 201
    assert created.json()["pending_confirmation"] is True
    assert "8025" in created.json()["message"]
    assert client.get("/api/v1/auth/me/").status_code == 403
    assert User.objects.get(email="nuevo@ejemplo.test").email_confirmed is False
    assert len(mail.outbox) == 1

    blocked = client.post(
        "/api/v1/auth/login/",
        {"email": "nuevo@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert blocked.status_code == 400
    assert blocked.json()["error"]["code"] == "email_unconfirmed"

    again = register(client, email="Nuevo@Ejemplo.Test", display_name="Otro")
    assert again.status_code == 400
    assert again.json()["error"]["message"] == "Ese correo ya está registrado."
    assert User.objects.filter(email__iexact="nuevo@ejemplo.test").count() == 1
    unknown = client.post(
        "/api/v1/auth/confirm-email/resend/",
        {"email": "nadie@ejemplo.test"},
        format="json",
    )
    assert unknown.status_code == 200
    assert len(mail.outbox) == 1

    query = _confirmation_query()
    bad = client.post(
        "/api/v1/auth/confirm-email/",
        {"uid": query["confirmar"][0], "token": "no-sirve"},
        format="json",
    )
    assert bad.status_code == 400
    confirmed = client.post(
        "/api/v1/auth/confirm-email/",
        {"uid": query["confirmar"][0], "token": query["token"][0]},
        format="json",
    )
    assert confirmed.status_code == 200, confirmed.content
    assert confirmed.json()["display_name"] == "Nuevo"
    refresh_csrf(client)
    assert client.get("/api/v1/auth/me/").status_code == 200
    assert User.objects.get(email="nuevo@ejemplo.test").email_confirmed is True
    duplicate = register(client, email="nuevo@ejemplo.test")
    assert duplicate.status_code == 400


@override_settings(
    EMAIL_CONFIRMATION_REQUIRED=True,
    TRAZA_PUBLIC_ORIGIN="http://127.0.0.1:18080",
    TRAZA_MAIL_UI="http://127.0.0.1:8025",
)
def test_confirmar_en_otro_equipo_permite_entrar_en_el_primero(client):
    created = register(client, email="nuevo@ejemplo.test", display_name="Nuevo")
    assert created.status_code == 201
    query = _confirmation_query()
    link = next(line for line in mail.outbox[-1].body.splitlines() if line.startswith("http"))
    assert "/api/v1/auth/confirm-email/open/" in link

    teacher = APIClient(enforce_csrf_checks=True)
    refresh_csrf(teacher)
    register(teacher, email="docente@ejemplo.test", role="teacher")
    User.objects.filter(email="docente@ejemplo.test").update(email_confirmed=True)
    refresh_csrf(teacher)
    entered = teacher.post(
        "/api/v1/auth/login/",
        {"email": "docente@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert entered.status_code == 200, entered.content
    refresh_csrf(teacher)
    kept = teacher.post(
        "/api/v1/auth/confirm-email/",
        {"uid": query["confirmar"][0], "token": query["token"][0]},
        format="json",
    )
    assert kept.status_code == 200, kept.content
    assert kept.json()["confirmed"] is True
    assert teacher.get("/api/v1/auth/me/").json()["email"] == "docente@ejemplo.test"

    refresh_csrf(client)
    logged = client.post(
        "/api/v1/auth/login/",
        {"email": "nuevo@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert logged.status_code == 200, logged.content
    assert logged.json()["email"] == "nuevo@ejemplo.test"


@override_settings(
    EMAIL_CONFIRMATION_REQUIRED=True,
    TRAZA_PUBLIC_ORIGIN="http://127.0.0.1:18080",
    TRAZA_MAIL_UI="http://127.0.0.1:8025",
)
def test_el_enlace_del_correo_confirma_aunque_otra_sesion_este_abierta(client):
    register(client, email="otro@ejemplo.test", display_name="Otro")
    query = _confirmation_query()
    teacher = APIClient(enforce_csrf_checks=True)
    refresh_csrf(teacher)
    register(teacher, email="docente.enlace@ejemplo.test", role="teacher")
    User.objects.filter(email="docente.enlace@ejemplo.test").update(email_confirmed=True)
    refresh_csrf(teacher)
    assert (
        teacher.post(
            "/api/v1/auth/login/",
            {"email": "docente.enlace@ejemplo.test", "password": PASSWORD},
            format="json",
        ).status_code
        == 200
    )
    opened = teacher.get(
        "/api/v1/auth/confirm-email/open/",
        {"confirmar": query["confirmar"][0], "token": query["token"][0]},
    )
    assert opened.status_code == 302
    assert opened["Location"] == "/?correo=confirmado"
    assert teacher.get("/api/v1/auth/me/").json()["email"] == "docente.enlace@ejemplo.test"
    assert User.objects.get(email="otro@ejemplo.test").email_confirmed is True

    fresh = APIClient(enforce_csrf_checks=True)
    refresh_csrf(fresh)
    again = register(fresh, email="libre@ejemplo.test")
    assert again.status_code == 201
    fresh_query = _confirmation_query()
    visitor = APIClient(enforce_csrf_checks=True)
    refresh_csrf(visitor)
    visited = visitor.get(
        "/api/v1/auth/confirm-email/open/",
        {"confirmar": fresh_query["confirmar"][0], "token": fresh_query["token"][0]},
    )
    assert visited.status_code == 302
    assert visited["Location"] == "/"
    assert visitor.get("/api/v1/auth/me/").json()["email"] == "libre@ejemplo.test"
    refresh_csrf(fresh)
    home = fresh.post(
        "/api/v1/auth/login/",
        {"email": "libre@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert home.status_code == 409, home.content
    assert home.json()["error"]["code"] == "session_open"
    assert visitor.get("/api/v1/auth/me/").status_code == 200


def test_login_rate_limit_and_csrf(client):
    for _ in range(2):
        failed = client.post(
            "/api/v1/auth/login/",
            {"email": "ana@ejemplo.test", "password": "mala"},
            format="json",
        )
        assert failed.status_code == 400
    blocked = client.post(
        "/api/v1/auth/login/",
        {"email": "ana@ejemplo.test", "password": "mala"},
        format="json",
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "login_locked"
    other = APIClient(enforce_csrf_checks=True)
    refresh_csrf(other)
    away = other.post(
        "/api/v1/auth/login/",
        {"email": "ana@ejemplo.test", "password": PASSWORD},
        format="json",
        REMOTE_ADDR="10.9.9.9",
    )
    assert away.status_code == 429
    assert away.json()["error"]["code"] == "login_locked"
    bare = APIClient(enforce_csrf_checks=True)
    denied = bare.post(
        "/api/v1/auth/login/",
        {"email": "a@b.co", "password": "x"},
        format="json",
        REMOTE_ADDR="10.1.1.1",
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "csrf_failed"


def test_una_sola_sesion_por_cuenta_y_se_cierra_por_inactividad(client, settings):
    created = register(client, email="unica@ejemplo.test", display_name="Unica")
    assert created.status_code == 201
    browser = APIClient(enforce_csrf_checks=True, HTTP_X_AULIVANA_FCDDESIGN_CLIENT="")
    refresh_csrf(browser)
    denied = browser.post(
        "/api/v1/auth/login/",
        {"email": "unica@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert denied.status_code == 409, denied.content
    assert denied.json()["error"]["code"] == "session_open"
    assert client.get("/api/v1/auth/me/").status_code == 200

    stored = client.session
    stored["last_activity"] = int(time.time()) - settings.SESSION_IDLE_SECONDS - 5
    stored.save()
    idle = client.get("/api/v1/auth/me/")
    assert idle.status_code == 401
    assert idle.json()["error"]["code"] == "session_idle"

    refresh_csrf(browser)
    entered = browser.post(
        "/api/v1/auth/login/",
        {"email": "unica@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert entered.status_code == 200, entered.content
    refresh_csrf(client)
    again = client.post(
        "/api/v1/auth/login/",
        {"email": "unica@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert again.status_code == 409
    assert browser.get("/api/v1/auth/me/").status_code == 200


def test_otra_ventana_del_navegador_no_entra(client):
    created = register(client, email="ventana@ejemplo.test", display_name="Ventana")
    assert created.status_code == 201
    owner = client.get("/api/v1/auth/me/", HTTP_X_TRAZA_WINDOW="ventana-aaaa")
    assert owner.status_code == 200, owner.content

    other = APIClient(enforce_csrf_checks=True, HTTP_X_TRAZA_WINDOW="ventana-bbbb")
    other.cookies["sessionid"] = client.cookies["sessionid"].value
    denied = other.get("/api/v1/auth/me/")
    assert denied.status_code == 401, denied.content
    assert denied.json()["error"]["code"] == "session_open"
    assert client.get("/api/v1/auth/me/", HTTP_X_TRAZA_WINDOW="ventana-aaaa").status_code == 200

    other.cookies["csrftoken"] = client.cookies["csrftoken"].value
    other.credentials(HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
    again = other.post(
        "/api/v1/auth/login/",
        {"email": "ventana@ejemplo.test", "password": PASSWORD},
        format="json",
        HTTP_X_TRAZA_WINDOW="ventana-bbbb",
    )
    assert again.status_code == 401, again.content
    assert again.json()["error"]["code"] == "session_open"
    assert client.get("/api/v1/auth/me/", HTTP_X_TRAZA_WINDOW="ventana-aaaa").status_code == 200

    stored = client.session
    stored["window_seen"] = int(time.time()) - 60
    stored.save()
    taken = other.get("/api/v1/auth/me/", HTTP_X_TRAZA_WINDOW="ventana-bbbb")
    assert taken.status_code == 200, taken.content
    blocked = client.get("/api/v1/auth/me/", HTTP_X_TRAZA_WINDOW="ventana-aaaa")
    assert blocked.status_code == 401
    assert blocked.json()["error"]["code"] == "session_open"


def test_duplicate_email_and_weak_password(client):
    assert register(client).status_code == 201
    other = APIClient(enforce_csrf_checks=True)
    refresh_csrf(other)
    again = register(other, email="Ana@ejemplo.test")
    assert again.status_code == 400
    assert again.json()["error"]["message"] == "Ese correo ya está registrado."
    assert User.objects.filter(email__iexact="ana@ejemplo.test").count() == 1
    weak = register(other, email="luz@ejemplo.test", password="123")
    assert weak.status_code == 400


def test_foreign_objects_are_not_found(client):
    register(client)
    project_id = client.post("/api/v1/projects/", {"name": "Privado"}, format="json").json()["id"]
    algorithm_id = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Secreto"},
        format="json",
    ).json()["id"]
    other = APIClient(enforce_csrf_checks=True)
    refresh_csrf(other)
    register(other, email="luis@ejemplo.test")
    assert other.get(f"/api/v1/projects/{project_id}/").status_code == 404
    assert (
        other.patch(f"/api/v1/projects/{project_id}/", {"name": "Robo"}, format="json").status_code
        == 404
    )
    assert other.get(f"/api/v1/algorithms/{algorithm_id}/").status_code == 404
    assert other.post(f"/api/v1/algorithms/{algorithm_id}/execute/").status_code == 404
    listed = other.get("/api/v1/algorithms/?page_size=100").json()["results"]
    assert algorithm_id not in {row["id"] for row in listed}
    assert "Secreto" not in {row["name"] for row in listed}
    by_project = other.get(f"/api/v1/algorithms/?project={project_id}&page_size=100")
    assert by_project.json()["results"] == []
    assert "no-store" in by_project.headers["Cache-Control"]
    projects = other.get("/api/v1/projects/").json()["results"]
    assert project_id not in {row["id"] for row in projects}


def test_autosave_versions_and_restore(client):
    register(client)
    project_id = _project_id(client)
    created = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Borrador", "source": "Algoritmo A\nFinAlgoritmo\n"},
        format="json",
    )
    assert created.status_code == 201
    algorithm_id = created.json()["id"]
    assert created.json()["current_version"] == 0
    assert AlgorithmVersion.objects.filter(algorithm_id=algorithm_id).count() == 0

    saved = client.patch(
        f"/api/v1/algorithms/{algorithm_id}/",
        {"source": "Algoritmo B\n    Escribir 1;\nFinAlgoritmo\n"},
        format="json",
    )
    assert saved.status_code == 200
    assert AlgorithmVersion.objects.filter(algorithm_id=algorithm_id).count() == 0

    first = client.post(
        f"/api/v1/algorithms/{algorithm_id}/save/", {"message": "listo"}, format="json"
    )
    assert first.json()["number"] == 1
    again = client.post(f"/api/v1/algorithms/{algorithm_id}/save/", {}, format="json")
    assert again.json()["number"] == 1
    client.patch(
        f"/api/v1/algorithms/{algorithm_id}/",
        {"source": "Algoritmo C\n    Escribir 2;\nFinAlgoritmo\n"},
        format="json",
    )
    second = client.post(f"/api/v1/algorithms/{algorithm_id}/save/", {}, format="json")
    assert second.json()["number"] == 2
    restored = client.post(f"/api/v1/algorithms/{algorithm_id}/versions/1/restore/")
    assert restored.status_code == 200
    assert restored.json()["number"] == 3
    numbers = [
        row["number"]
        for row in client.get(f"/api/v1/algorithms/{algorithm_id}/versions/").json()["results"]
    ]
    assert numbers == [1, 2, 3]
    assert (
        client.get(f"/api/v1/algorithms/{algorithm_id}/").json()["source"] == first.json()["source"]
    )


def test_translate_returns_python_without_creating_an_execution(client):
    register(client)
    project_id = _project_id(client)
    algorithm_id = client.post(
        "/api/v1/algorithms/",
        {
            "project_id": project_id,
            "name": "Hola",
            "source": 'Algoritmo Hola\n    Escribir "Hola";\nFinAlgoritmo\n',
        },
        format="json",
    ).json()["id"]
    translated = client.post(f"/api/v1/algorithms/{algorithm_id}/translate/")
    assert translated.status_code == 200
    body = translated.json()
    python = next(item for item in body["translations"] if item["language"] == "python")
    assert 'print("Hola")' in python["code"]
    assert Execution.objects.count() == 0


def test_validate_does_not_execute_and_errors_keep_line(client):
    register(client)
    project_id = _project_id(client)
    algorithm_id = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Roto", "source": MISSING_END},
        format="json",
    ).json()["id"]
    checked = client.post(f"/api/v1/algorithms/{algorithm_id}/validate/")
    assert checked.status_code == 200
    assert any(item["code"] == "E0202" for item in checked.json()["diagnostics"])
    assert Execution.objects.count() == 0


def test_execute_persists_output_and_error_not_lines(client):
    register(client)
    project_id = _project_id(client)
    algorithm_id = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Falla", "source": RUNTIME_ERROR},
        format="json",
    ).json()["id"]
    ran = _execute(client, algorithm_id)
    assert ran.status_code == 200
    body = ran.json()
    assert body["status"] == "error"
    assert "antes" in body["output"]
    assert any(item["code"] == "E0401" for item in body["diagnostics"])
    execution = Execution.objects.get(id=body["id"])
    kinds = set(execution.events.values_list("kind", flat=True))
    assert "output" in kinds
    assert "error" in kinds
    assert "line" not in kinds
    assert ExecutionEvent.objects.filter(execution=execution, kind="line").count() == 0
    assert AuditEvent.objects.filter(action="execution.start").exists()


def test_execute_publishes_each_console_frame(client, monkeypatch):
    monkeypatch.setattr("language_core.debugger.pause_for", lambda *_args, **_kwargs: None)
    register(client)
    project_id = _project_id(client)
    source = """Algoritmo Animacion
    Escribir "Hola";
    Borrar Pantalla;
    Escribir "Listo";
    Esperar 1 Segundos;
FinAlgoritmo
"""
    algorithm_id = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Animacion", "source": source},
        format="json",
    ).json()["id"]
    paused = client.post(f"/api/v1/algorithms/{algorithm_id}/execute/")
    assert paused.status_code == 201
    assert paused.json()["status"] == "paused"
    assert paused.json()["debug"] is False
    finished = client.post(
        f"/api/v1/executions/{paused.json()['id']}/control/",
        {"action": "continue"},
        format="json",
    )
    assert finished.status_code == 200
    assert finished.json()["status"] == "completed"
    assert finished.json()["output"] == "Listo\n"
    live = peek(paused.json()["id"])
    assert live is not None
    frames = [event.get("output") for event in live.events if event.get("event") == "output"]
    assert frames == ["Hola\n", "", "Listo\n"]


def test_console_retries_invalid_input(client):
    register(client)
    project_id = _project_id(client)
    algorithm_id = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Lee", "source": READ_NUMBER},
        format="json",
    ).json()["id"]
    paused = client.post(f"/api/v1/algorithms/{algorithm_id}/execute/").json()
    assert paused["status"] == "paused"
    assert paused["debug"] is False
    started = client.post(
        f"/api/v1/executions/{paused['id']}/control/",
        {"action": "continue"},
        format="json",
    ).json()
    assert started["status"] == "waiting_input"
    assert started["pending_input"] == {"name": "n", "type": "entero"}
    rejected = client.post(
        f"/api/v1/executions/{started['id']}/input/",
        {"text": "no"},
        format="json",
    ).json()
    assert rejected["status"] == "waiting_input"
    assert any(item["code"] == "E0406" for item in rejected["diagnostics"])
    assert ExecutionEvent.objects.filter(execution_id=started["id"], kind="input").count() == 0
    accepted = client.post(
        f"/api/v1/executions/{started['id']}/input/",
        {"text": "4"},
        format="json",
    ).json()
    assert accepted["status"] == "completed"
    assert accepted["output"] == "4\n4\n"
    assert list(
        ExecutionEvent.objects.filter(execution_id=started["id"], kind="input").values_list(
            "text", flat=True
        )
    ) == ["4"]


def test_execute_rate_limit_does_not_multiply_versions(client):
    register(client)
    algorithm_id = _algorithm(client, "Hola mundo")["id"]
    for _ in range(3):
        response = _execute(client, algorithm_id)
        assert response.status_code == 200
        assert response.json()["output"] == "Hola mundo\n"
    blocked = client.post(f"/api/v1/algorithms/{algorithm_id}/execute/")
    assert blocked.status_code == 429
    assert AlgorithmVersion.objects.filter(algorithm_id=algorithm_id).count() == 1


def test_share_link_hides_revoked_and_expired(client):
    register(client)
    algorithm_id = _algorithm(client, "Hola mundo")["id"]
    created = client.post(f"/api/v1/algorithms/{algorithm_id}/share/", {}, format="json")
    assert created.status_code == 201
    token = created.json()["token"]
    shared = APIClient()
    assert "Hola mundo" in shared.get(f"/api/v1/shared/{token}/").json()["source"]
    assert client.delete(f"/api/v1/share-links/{created.json()['id']}/").status_code == 204
    assert shared.get(f"/api/v1/shared/{token}/").status_code == 404
    expired = client.post(
        f"/api/v1/algorithms/{algorithm_id}/share/",
        {"expires_at": "2000-01-01T00:00:00Z"},
        format="json",
    )
    assert shared.get(f"/api/v1/shared/{expired.json()['token']}/").status_code == 404


def test_preferences_save_locale_mode_and_language_without_rewriting_source(client):
    register(client, email="idioma@ejemplo.test")
    existing = _algorithm(client, "Hola mundo")
    source = existing["source"]

    updated = client.patch(
        "/api/v1/preferences/",
        {
            "locale": "en",
            "theme": "dark",
            "require_semicolons": False,
            "index_base": 0,
        },
        format="json",
    )
    assert updated.status_code == 200
    stored = client.get("/api/v1/preferences/").json()
    assert stored["locale"] == "en"
    assert stored["theme"] == "dark"
    assert stored["require_semicolons"] is False
    assert stored["index_base"] == 0

    refused = client.patch("/api/v1/auth/me/", {"role": "teacher"}, format="json")
    assert refused.status_code == 400
    assert client.get("/api/v1/auth/me/").json()["role"] == "student"

    kept = client.get(f"/api/v1/algorithms/{existing['id']}/").json()
    assert kept["source"] == source
    assert kept["require_semicolons"] is True
    assert kept["index_base"] == 1

    created = client.post(
        "/api/v1/algorithms/",
        {"project_id": existing["project_id"], "name": "Con la preferencia"},
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["require_semicolons"] is False
    assert created.json()["index_base"] == 0
    assert created.json()["source"].startswith("Algorithm ")
    assert 'Write "Hello";' in created.json()["source"]

    rejected = client.patch(
        "/api/v1/preferences/", {"locale": "fr", "index_base": 2}, format="json"
    )
    assert rejected.status_code == 400
    assert client.get("/api/v1/preferences/").json()["locale"] == "en"


def test_preferences_theme_and_trash(client):
    register(client)
    updated = client.patch(
        "/api/v1/preferences/", {"theme": "dark", "font_size": 18}, format="json"
    )
    assert updated.status_code == 200
    assert updated.json()["theme"] == "dark"
    project_id = client.post("/api/v1/projects/", {"name": "Temporal"}, format="json").json()["id"]
    assert client.delete(f"/api/v1/projects/{project_id}/").status_code == 204
    assert client.get(f"/api/v1/projects/{project_id}/").status_code == 404
    restored = client.post(f"/api/v1/projects/{project_id}/restore/")
    assert restored.status_code == 200
    assert restored.json()["name"] == "Temporal"


def test_folders_reject_depth_and_cycles(client):
    register(client)
    project_id = _project_id(client)
    parent = None
    for index in range(8):
        payload = {"name": f"Nivel {index}"}
        if parent:
            payload["parent_id"] = parent
        created = client.post(f"/api/v1/projects/{project_id}/folders/", payload, format="json")
        assert created.status_code == 201, created.json()
        parent = created.json()["id"]
    too_deep = client.post(
        f"/api/v1/projects/{project_id}/folders/",
        {"name": "De más", "parent_id": parent},
        format="json",
    )
    assert too_deep.status_code == 400
    root = client.post(
        f"/api/v1/projects/{project_id}/folders/", {"name": "Raíz"}, format="json"
    ).json()["id"]
    child = client.post(
        f"/api/v1/projects/{project_id}/folders/",
        {"name": "Hija", "parent_id": root},
        format="json",
    ).json()["id"]
    cycle = client.patch(f"/api/v1/folders/{root}/", {"parent_id": child}, format="json")
    assert cycle.status_code == 400


def test_limits_and_unknown_profile(client, settings):
    register(client)
    settings.MAX_PROJECTS_PER_USER = 1
    assert client.post("/api/v1/projects/", {"name": "Otro"}, format="json").status_code == 400
    settings.MAX_PROJECTS_PER_USER = 50
    project_id = _project_id(client)
    settings.MAX_ALGORITHMS_PER_PROJECT = len(EXAMPLES)
    capped = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Extra"},
        format="json",
    )
    assert capped.status_code == 400
    settings.MAX_ALGORITHMS_PER_PROJECT = 200
    huge = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Grande", "source": "x" * (64 * 1024 + 1)},
        format="json",
    )
    assert huge.status_code == 400
    unknown = client.post(
        "/api/v1/algorithms/",
        {"project_id": project_id, "name": "Raro", "language_profile": "no-existe"},
        format="json",
    )
    assert unknown.status_code == 404


def test_algorithm_can_drop_semicolons_and_start_indexes_at_zero(client):
    register(client, email="opciones@ejemplo.test")
    algorithm_id = _algorithm(client, "Hola mundo")["id"]
    created = client.get(f"/api/v1/algorithms/{algorithm_id}/").json()
    assert created["require_semicolons"] is True
    assert created["index_base"] == 1

    rejected = client.patch(
        f"/api/v1/algorithms/{algorithm_id}/",
        {"index_base": 2},
        format="json",
    )
    assert rejected.status_code == 400

    optional = client.patch(
        f"/api/v1/algorithms/{algorithm_id}/",
        {"require_semicolons": False, "index_base": 0},
        format="json",
    )
    assert optional.status_code == 200
    assert optional.json()["require_semicolons"] is False
    assert optional.json()["index_base"] == 0

    source = """Algoritmo Indices
    Definir a Como Entero
    Dimension a[2] Como Entero
    a[0] <- 7
    Escribir a[0]
FinAlgoritmo
"""
    client.patch(f"/api/v1/algorithms/{algorithm_id}/", {"source": source}, format="json")
    checked = client.post(f"/api/v1/algorithms/{algorithm_id}/validate/")
    assert checked.status_code == 200
    assert checked.json()["diagnostics"] == []
    ran = _execute(client, algorithm_id)
    assert ran.status_code == 200
    assert ran.json()["output"] == "7\n"

    back = client.patch(
        f"/api/v1/algorithms/{algorithm_id}/",
        {"index_base": 1},
        format="json",
    )
    assert back.status_code == 200
    out_of_range = _execute(client, algorithm_id)
    assert out_of_range.json()["status"] == "error"


def test_system_profile_cannot_be_deleted(db):
    profile = LanguageProfile.objects.get(key="strict")
    with pytest.raises(DomainError):
        profile.delete()


def test_inprocess_runner_refuses_production_debug(settings):
    settings.DEBUG = False
    with pytest.raises(ImproperlyConfigured, match="en proceso"):
        run_in_process("Algoritmo A\nFinAlgoritmo\n", [], STRICT)


def test_production_settings_refuse_the_inprocess_runner():
    import importlib

    with pytest.raises(ImproperlyConfigured, match="en proceso"):
        importlib.import_module("config.settings.production")


def test_development_settings_keep_the_inprocess_runner(monkeypatch):
    import importlib

    monkeypatch.delenv("TRAZA_RUNNER", raising=False)
    from config.settings import development

    reloaded = importlib.reload(development)
    assert reloaded.DEBUG is True
    assert reloaded.EXECUTION_RUNNER == "inprocess"


def test_finished_execution_rejects_more_input(client):
    register(client)
    algorithm_id = _algorithm(client, "Hola mundo")["id"]
    started = _execute(client, algorithm_id).json()
    rejected = client.post(
        f"/api/v1/executions/{started['id']}/input/", {"text": "x"}, format="json"
    )
    assert rejected.status_code == 409
