"""Niveles, navegador de la cuenta y administrador creado por comando."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.billing.models import Plan
from apps.tests.helpers import PASSWORD, refresh_csrf, register

pytestmark = pytest.mark.django_db


def test_el_alta_no_acepta_administrador(client):
    refused = register(client, email="admin-publico@ejemplo.test", role="admin")
    assert refused.status_code == 400


def test_el_plan_gratis_limita_proyectos_y_abre_el_navegador(settings):
    settings.TRAZA_SIGNUP_PLAN = "gratis"
    browser = APIClient(enforce_csrf_checks=True, HTTP_X_AULIVANA_FCDDESIGN_CLIENT="")
    refresh_csrf(browser)
    created = register(browser, email="gratis@ejemplo.test", display_name="Gratis")
    assert created.status_code == 201, created.content
    body = created.json()
    assert body["plan"]["code"] == "gratis"
    assert body["access"]["browser_app"] is True
    assert body["access"]["features"]["execute"] is True
    assert body["access"]["features"]["translate"] is False
    assert body["access"]["features"]["languages"] is False
    assert body["access"]["limits"]["max_executions_per_day"] == 3
    assert body["usage"]["executions_today"] == 0
    assert browser.get("/api/v1/auth/me/").status_code == 200
    opened = browser.get("/api/v1/projects/")
    assert opened.status_code == 200
    assert browser.post("/api/v1/auth/logout/").status_code == 204

    desktop = APIClient(enforce_csrf_checks=True)
    refresh_csrf(desktop)
    entered = desktop.post(
        "/api/v1/auth/login/",
        {"email": "gratis@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert entered.status_code == 200, entered.content
    refresh_csrf(desktop)
    first = desktop.post("/api/v1/projects/", {"name": "Uno"}, format="json")
    second = desktop.post("/api/v1/projects/", {"name": "Dos"}, format="json")
    third = desktop.post("/api/v1/projects/", {"name": "Tres"}, format="json")
    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 403
    assert third.json()["error"]["code"] == "plan_limit"


def test_un_nivel_vencido_vuelve_a_las_funciones_gratis(client, settings):
    settings.TRAZA_SIGNUP_PLAN = "premium"
    created = register(client, email="vence@ejemplo.test")
    assert created.json()["access"]["features"]["translate"] is True
    subscription = client.get("/api/v1/auth/me/").json()
    assert subscription["plan"]["code"] == "premium"
    from apps.accounts.models import User
    from apps.billing.models import Subscription

    user = User.objects.get(email="vence@ejemplo.test")
    sub = Subscription.objects.get(user=user)
    sub.paid_until = timezone.now() - timedelta(days=1)
    sub.save(update_fields=["paid_until"])
    current = client.get("/api/v1/auth/me/").json()
    assert current["plan"]["status"] == "expired"
    assert current["plan"]["days_remaining"] == 0
    assert current["access"]["features"]["translate"] is False
    assert current["access"]["features"]["execute"] is True


def test_el_administrador_define_un_nivel_y_lo_asigna(client):
    call_command("create_admin", email="admin@ejemplo.test", password=PASSWORD, name="Ada")
    register(client, email="alumno-nivel@ejemplo.test", display_name="Luz")
    admin = APIClient(enforce_csrf_checks=True, HTTP_X_AULIVANA_FCDDESIGN_CLIENT="")
    refresh_csrf(admin)
    entered = admin.post(
        "/api/v1/auth/login/",
        {"email": "admin@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert entered.status_code == 200, entered.content
    assert entered.json()["role"] == "admin"
    refresh_csrf(admin)
    listed = admin.get("/api/v1/billing/plans/")
    assert listed.status_code == 200
    codes = {item["code"] for item in listed.json()["results"]}
    assert {"gratis", "premium"} <= codes
    created = admin.post(
        "/api/v1/billing/plans/",
        {
            "code": "escuela",
            "name": "Escuela",
            "audience": "student",
            "price_cents": 15000,
            "currency": "MXN",
            "period_days": 90,
            "browser_allowed": False,
            "max_projects": 4,
            "max_algorithms": None,
            "features": {
                "editor": True,
                "execute": True,
                "lab": True,
                "lab_route": True,
                "lab_practice": True,
            },
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    assert created.json()["max_executions_per_day"] == 3
    plan_id = created.json()["id"]
    people = admin.get("/api/v1/billing/users/?q=luz")
    assert people.status_code == 200
    person = people.json()["results"][0]
    assigned = admin.patch(
        f"/api/v1/billing/users/{person['id']}/",
        {"plan_id": plan_id},
        format="json",
    )
    assert assigned.status_code == 200, assigned.content
    assert assigned.json()["plan"]["code"] == "escuela"
    assert Plan.objects.get(audience="student", code="escuela").price_cents == 15000
    denied = client.get("/api/v1/billing/plans/")
    assert denied.status_code == 403
    catalog = admin.get("/api/v1/billing/catalog/")
    assert catalog.status_code == 200
    assert any(
        item["key"] == "languages" and item["label"] == "Lenguajes"
        for item in catalog.json()["results"]
    )
    gratis = next(
        item
        for item in listed.json()["results"]
        if item["code"] == "gratis" and item["audience"] == "student"
    )
    assert gratis["features"]["languages"] is False
    enabled = admin.patch(
        f"/api/v1/billing/plans/{gratis['id']}/",
        {"features": {**gratis["features"], "languages": True}},
        format="json",
    )
    assert enabled.status_code == 200, enabled.content
    assert enabled.json()["features"]["languages"] is True
    assert enabled.json()["features"]["execute"] is True


def test_sin_comunidades_el_docente_sigue_viendo_sus_proyectos(client):
    created = register(client, email="docente-editor@ejemplo.test", role="teacher")
    assert created.status_code == 201, created.content
    from apps.accounts.models import User
    from apps.billing.models import Plan
    from apps.billing.services import update_plan

    user = User.objects.get(email="docente-editor@ejemplo.test")
    plan = user.subscription.plan
    assert plan.code in {"gratis", "premium"}
    update_plan(plan, {"features": {**plan.features, "communities": False, "editor": True}})
    me = client.get("/api/v1/auth/me/").json()
    assert me["access"]["features"]["communities"] is False
    assert me["access"]["features"]["editor"] is True
    own = client.get("/api/v1/projects/")
    assert own.status_code == 200, own.content
    listed = own.json()["results"]
    assert listed
    first = listed[0]["id"]
    codes = client.get(f"/api/v1/algorithms/?project={first}")
    assert codes.status_code == 200, codes.content
    blocked = client.get("/api/v1/classroom/students/")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "plan_forbidden"
    assert client.get("/api/v1/communities/").status_code == 403
    update_plan(plan, {"features": {**plan.features, "communities": True}})
    assert client.get("/api/v1/communities/").status_code == 200


def test_una_cuenta_puede_usar_el_navegador_aunque_el_nivel_no(settings):
    settings.TRAZA_SIGNUP_PLAN = "gratis"
    call_command("create_admin", email="admin-web@ejemplo.test", password=PASSWORD)
    browser = APIClient(enforce_csrf_checks=True, HTTP_X_AULIVANA_FCDDESIGN_CLIENT="")
    refresh_csrf(browser)
    created = register(browser, email="web@ejemplo.test", display_name="Roque")
    assert created.json()["access"]["browser_app"] is True
    admin = APIClient(enforce_csrf_checks=True, HTTP_X_AULIVANA_FCDDESIGN_CLIENT="")
    refresh_csrf(admin)
    assert (
        admin.post(
            "/api/v1/auth/login/",
            {"email": "admin-web@ejemplo.test", "password": PASSWORD},
            format="json",
        ).status_code
        == 200
    )
    refresh_csrf(admin)
    listed = admin.get("/api/v1/billing/users/?page_size=1")
    assert listed.status_code == 200
    body = listed.json()
    assert body["page"] == 1
    assert body["pages"] == body["count"]
    assert len(body["results"]) == 1
    person = admin.get("/api/v1/billing/users/?q=web@ejemplo.test").json()["results"][0]
    assert person["browser_allowed"] is True
    assert browser.get("/api/v1/projects/").status_code == 200
    closed = admin.patch(
        f"/api/v1/billing/users/{person['id']}/",
        {"browser_allowed": None},
        format="json",
    )
    assert closed.status_code == 200, closed.content
    assert closed.json()["browser_allowed"] is None
    refused = browser.get("/api/v1/projects/")
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "browser_forbidden"
    opened = admin.patch(
        f"/api/v1/billing/users/{person['id']}/",
        {"browser_allowed": True},
        format="json",
    )
    assert opened.status_code == 200, opened.content
    assert opened.json()["browser_allowed"] is True
    current = browser.get("/api/v1/auth/me/")
    assert current.status_code == 200
    assert current.json()["access"]["browser_app"] is True
    assert browser.get("/api/v1/projects/").status_code == 200


def test_el_administrador_elige_que_cuentas_se_pueden_crear(client):
    opened = client.get("/api/v1/auth/signup/")
    assert opened.status_code == 200
    assert opened.json() == {"student": True, "teacher": True}

    call_command("create_admin", email="admin-altas@ejemplo.test", password=PASSWORD, name="Ada")
    admin = APIClient(enforce_csrf_checks=True)
    refresh_csrf(admin)
    entered = admin.post(
        "/api/v1/auth/login/",
        {"email": "admin-altas@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert entered.status_code == 200, entered.content
    refresh_csrf(admin)

    refused = client.patch("/api/v1/auth/signup/", {"teacher": False}, format="json")
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "not_authenticated"

    closed = admin.patch("/api/v1/auth/signup/", {"teacher": False}, format="json")
    assert closed.status_code == 200, closed.content
    assert closed.json() == {"student": True, "teacher": False}
    teacher = register(client, email="alta-docente@ejemplo.test", role="teacher")
    assert teacher.status_code == 400
    assert "docente" in teacher.json()["error"]["message"]
    student = register(client, email="alta-alumno@ejemplo.test", role="student")
    assert student.status_code == 201, student.content

    both = admin.patch(
        "/api/v1/auth/signup/",
        {"student": False, "teacher": False},
        format="json",
    )
    assert both.status_code == 200
    blocked = register(client, email="alta-cerrada@ejemplo.test")
    assert blocked.status_code == 400
    assert "alumno" in blocked.json()["error"]["message"]


def test_la_cuenta_incluye_access_si_no_hay_niveles(client):
    created = register(client, email="sin-nivel@ejemplo.test")
    assert created.status_code == 201
    from apps.billing.models import Subscription

    Subscription.objects.all().delete()
    Plan.objects.all().delete()
    current = client.get("/api/v1/auth/me/")
    assert current.status_code == 200
    body = current.json()
    assert body["access"]["browser_app"] is False
    assert "features" in body["access"]


def test_el_admin_pone_el_tope_diario_o_lo_deja_sin_limite(client):
    call_command("create_admin", email="admin-cupo@ejemplo.test", password=PASSWORD, name="Ada")
    admin = APIClient(enforce_csrf_checks=True, HTTP_X_AULIVANA_FCDDESIGN_CLIENT="")
    refresh_csrf(admin)
    entered = admin.post(
        "/api/v1/auth/login/",
        {"email": "admin-cupo@ejemplo.test", "password": PASSWORD},
        format="json",
    )
    assert entered.status_code == 200, entered.content
    refresh_csrf(admin)
    listed = admin.get("/api/v1/billing/plans/")
    gratis = next(
        item
        for item in listed.json()["results"]
        if item["code"] == "gratis" and item["audience"] == "student"
    )
    assert gratis["max_executions_per_day"] == 3
    refused = admin.patch(
        f"/api/v1/billing/plans/{gratis['id']}/",
        {"max_executions_per_day": 2},
        format="json",
    )
    assert refused.status_code == 400
    opened = admin.patch(
        f"/api/v1/billing/plans/{gratis['id']}/",
        {"max_executions_per_day": None},
        format="json",
    )
    assert opened.status_code == 200, opened.content
    assert opened.json()["max_executions_per_day"] is None
    capped = admin.patch(
        f"/api/v1/billing/plans/{gratis['id']}/",
        {"max_executions_per_day": 5},
        format="json",
    )
    assert capped.status_code == 200
    assert capped.json()["max_executions_per_day"] == 5


@override_settings(RATE_LIMITS={"execution.start": (30, 60)})
def test_el_nivel_limita_las_ejecuciones_del_dia(client, settings):
    settings.TRAZA_SIGNUP_PLAN = "gratis"
    created = register(client, email="cupo-run@ejemplo.test")
    assert created.status_code == 201, created.content
    from apps.accounts.models import User

    user = User.objects.get(email="cupo-run@ejemplo.test")
    plan = user.subscription.plan
    plan.max_executions_per_day = 3
    plan.features = {**plan.features, "languages": True}
    plan.save(update_fields=["max_executions_per_day", "features"])

    rows = client.get("/api/v1/algorithms/?page_size=100").json()["results"]
    algorithm_id = next(row["id"] for row in rows if row["name"] == "Hola mundo")
    first = client.post(f"/api/v1/algorithms/{algorithm_id}/execute/")
    second = client.post(f"/api/v1/algorithms/{algorithm_id}/execute/")
    language = client.post(
        "/api/v1/languages/open/",
        {"language": "python", "source": 'print("hola")\n'},
        format="json",
    )
    blocked = client.post(f"/api/v1/algorithms/{algorithm_id}/execute/")
    assert first.status_code == 201, first.content
    assert second.status_code == 201, second.content
    assert language.status_code == 200, language.content
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "plan_limit"
    me = client.get("/api/v1/auth/me/").json()
    assert me["access"]["limits"]["max_executions_per_day"] == 3
    assert me["usage"]["executions_today"] == 3


@override_settings(RATE_LIMITS={"execution.start": (30, 60)})
def test_sin_tope_el_nivel_deja_seguir_ejecutando(client):
    created = register(client, email="cupo-libre@ejemplo.test")
    assert created.status_code == 201, created.content
    assert created.json()["access"]["limits"]["max_executions_per_day"] is None
    rows = client.get("/api/v1/algorithms/?page_size=100").json()["results"]
    algorithm_id = next(row["id"] for row in rows if row["name"] == "Hola mundo")
    for _index in range(4):
        ran = client.post(f"/api/v1/algorithms/{algorithm_id}/execute/")
        assert ran.status_code == 201, ran.content
