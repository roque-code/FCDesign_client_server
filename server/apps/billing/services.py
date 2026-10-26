"""Lectura del nivel efectivo. No abre peticiones nuevas: viaja en la cuenta."""

from __future__ import annotations

import math
import re
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.models import Profile, User
from apps.billing.catalog import FEATURES, features_for, known_key
from apps.billing.models import DailyExecution, Plan, Subscription
from apps.projects.models import Algorithm, Project
from config.errors import DomainError

MIN_DAILY_RUNS = 3

DESKTOP_CLIENT = "desktop"
_CODE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_EXAMPLE = Q(name="Ejemplos", description="Algoritmos de ejemplo")

_FREE_STUDENT = {
    "editor": True,
    "diagram": False,
    "compose": False,
    "validate": True,
    "translate": False,
    "languages": False,
    "execute": True,
    "debug": False,
    "download": False,
    "paste": True,
    "lab": True,
    "lab_route": True,
    "lab_practice": True,
}
_FREE_TEACHER = {
    "editor": True,
    "diagram": True,
    "compose": False,
    "validate": True,
    "translate": False,
    "languages": False,
    "execute": True,
    "debug": False,
    "download": False,
    "paste": True,
    "lab": True,
    "lab_route": True,
    "lab_practice": True,
    "communities": False,
    "lab_bank": False,
    "lab_routes": False,
    "lab_progress": True,
}
_PREMIUM_STUDENT = {key: True for key in _FREE_STUDENT}
_PREMIUM_STUDENT["languages"] = False
_PREMIUM_TEACHER = {key: True for key in _FREE_TEACHER}
_PREMIUM_TEACHER["languages"] = False


def seed_definitions() -> list[dict[str, Any]]:
    """Valores iniciales. La pantalla de administrador los cambia después."""
    return [
        {
            "code": "gratis",
            "name": "Gratis",
            "audience": Plan.STUDENT,
            "price_cents": 0,
            "period_days": 0,
            "browser_allowed": False,
            "max_projects": 2,
            "max_algorithms": 5,
            "features": _FREE_STUDENT,
            "is_default": True,
            "sort_order": 0,
        },
        {
            "code": "premium",
            "name": "Premium",
            "audience": Plan.STUDENT,
            "price_cents": 0,
            "period_days": 30,
            "browser_allowed": False,
            "max_projects": None,
            "max_algorithms": None,
            "features": _PREMIUM_STUDENT,
            "is_default": False,
            "sort_order": 1,
        },
        {
            "code": "gratis",
            "name": "Gratis",
            "audience": Plan.TEACHER,
            "price_cents": 0,
            "period_days": 0,
            "browser_allowed": False,
            "max_projects": 3,
            "max_algorithms": 10,
            "features": _FREE_TEACHER,
            "is_default": True,
            "sort_order": 0,
        },
        {
            "code": "premium",
            "name": "Premium",
            "audience": Plan.TEACHER,
            "price_cents": 0,
            "period_days": 30,
            "browser_allowed": False,
            "max_projects": None,
            "max_algorithms": None,
            "features": _PREMIUM_TEACHER,
            "is_default": False,
            "sort_order": 1,
        },
    ]


def blank_features(audience: str) -> dict[str, bool]:
    return {item.key: False for item in features_for(audience)}


def normalize_features(audience: str, raw: object) -> dict[str, bool]:
    if not isinstance(raw, dict):
        raise DomainError("Las funciones del nivel no son válidas.")
    cleaned = blank_features(audience)
    for key, value in raw.items():
        if not isinstance(key, str) or not known_key(audience, key):
            raise DomainError("Hay una función que este tipo de cuenta no usa.")
        if not isinstance(value, bool):
            raise DomainError("Cada función se enciende o se apaga.")
        cleaned[key] = value
    return cleaned


def client_is_desktop(request) -> bool:
    header = request.META.get("HTTP_X_AULIVANA_FCDDESIGN_CLIENT", "")
    return isinstance(header, str) and header == DESKTOP_CLIENT


def _signup_plan(audience: str) -> Plan:
    code = getattr(settings, "TRAZA_SIGNUP_PLAN", "gratis")
    chosen = Plan.objects.filter(audience=audience, code=code, is_active=True).first()
    if chosen is not None:
        return chosen
    return Plan.objects.get(audience=audience, is_default=True)


def assign_default_subscription(user: User) -> Subscription | None:
    role = user.profile.role
    if role == Profile.ADMIN:
        return None
    audience = role if role in (Plan.STUDENT, Plan.TEACHER) else Plan.STUDENT
    plan = _signup_plan(audience)
    until = timezone.now() + timedelta(days=plan.period_days) if plan.period_days else None
    subscription, _created = Subscription.objects.get_or_create(
        user=user,
        defaults={"plan": plan, "paid_until": until, "browser_allowed": True},
    )
    return subscription


def _current(plan: Plan, paid_until) -> bool:
    if plan.is_default or plan.period_days == 0:
        return True
    if paid_until is None:
        return False
    return paid_until >= timezone.now()


def _fallback(plan: Plan) -> Plan:
    return Plan.objects.get(audience=plan.audience, is_default=True)


def _remaining(paid_until) -> int | None:
    if paid_until is None:
        return None
    seconds = (paid_until - timezone.now()).total_seconds()
    if seconds <= 0:
        return 0
    return math.ceil(seconds / 86400)


def _usage(user: User) -> dict[str, int]:
    projects = Project.objects.filter(owner=user).exclude(_EXAMPLE).count()
    algorithms = (
        Algorithm.objects.filter(owner=user, project__deleted_at__isnull=True)
        .exclude(project__name="Ejemplos", project__description="Algoritmos de ejemplo")
        .count()
    )
    return {
        "projects": projects,
        "algorithms": algorithms,
        "executions_today": _runs_today(user),
    }


def _runs_today(user: User) -> int:
    row = DailyExecution.objects.filter(user=user, day=timezone.localdate()).first()
    return 0 if row is None else row.count


def _features_of(plan: Plan) -> dict[str, bool]:
    stored = plan.features if isinstance(plan.features, dict) else {}
    cleaned = blank_features(plan.audience)
    for key in cleaned:
        cleaned[key] = stored.get(key) is True
    return cleaned


def account_access(user: User) -> dict[str, object]:
    """Plan asignado, nivel que aplica hoy y contadores. Una sola lectura de la cuenta."""
    if user.profile.role == Profile.ADMIN:
        return {
            "plan": None,
            "access": {
                "browser_app": True,
                "features": {item.key: False for item in FEATURES},
                "limits": {
                    "max_projects": 0,
                    "max_algorithms": 0,
                    "max_executions_per_day": 0,
                },
            },
            "usage": {"projects": 0, "algorithms": 0, "executions_today": 0},
        }
    try:
        subscription = user.subscription
    except Subscription.DoesNotExist:
        try:
            subscription = assign_default_subscription(user)
        except Exception:
            subscription = None
    if subscription is None:
        return {
            "plan": None,
            "access": {
                "browser_app": False,
                "features": {item.key: False for item in FEATURES},
                "limits": {
                    "max_projects": None,
                    "max_algorithms": None,
                    "max_executions_per_day": None,
                },
            },
            "usage": _usage(user),
        }
    assigned = subscription.plan
    active = _current(assigned, subscription.paid_until)
    effective = assigned if active else _fallback(assigned)
    features = _features_of(effective)
    return {
        "plan": {
            "code": assigned.code,
            "name": assigned.name,
            "audience": assigned.audience,
            "price_cents": assigned.price_cents,
            "currency": assigned.currency,
            "period_days": assigned.period_days,
            "status": "active" if active else "expired",
            "paid_until": (
                None if subscription.paid_until is None else subscription.paid_until.isoformat()
            ),
            "days_remaining": _remaining(subscription.paid_until),
        },
        "access": {
            "browser_app": (
                effective.browser_allowed
                if subscription.browser_allowed is None
                else subscription.browser_allowed
            ),
            "features": features,
            "limits": {
                "max_projects": effective.max_projects,
                "max_algorithms": effective.max_algorithms,
                "max_executions_per_day": effective.max_executions_per_day,
            },
        },
        "usage": _usage(user),
    }


def allows(user: User, *keys: str) -> bool:
    if user.profile.role == Profile.ADMIN:
        return False
    features = account_access(user)["access"]["features"]
    assert isinstance(features, dict)
    return any(features.get(key) is True for key in keys)


def ensure_quota(user: User, kind: str) -> None:
    if user.profile.role == Profile.ADMIN:
        raise DomainError("Esta cuenta administra los niveles.", status_code=403)
    access = account_access(user)
    limits = access["access"]["limits"]
    usage = access["usage"]
    assert isinstance(limits, dict) and isinstance(usage, dict)
    if kind == "project":
        limit = limits["max_projects"]
        if limit is not None and int(usage["projects"]) >= int(limit):
            raise DomainError(
                "Tu nivel no permite más proyectos.", code="plan_limit", status_code=403
            )
        return
    limit = limits["max_algorithms"]
    if limit is not None and int(usage["algorithms"]) >= int(limit):
        raise DomainError("Tu nivel no permite más algoritmos.", code="plan_limit", status_code=403)


def consume_execution(user: User) -> dict[str, int | None]:
    """Cobra una ejecución del día. Vacío en el nivel = sin tope."""
    if user.profile.role == Profile.ADMIN:
        raise DomainError(
            "Esta cuenta administra los niveles.", code="admin_account", status_code=403
        )
    access = account_access(user)
    limits = access["access"]["limits"]
    assert isinstance(limits, dict)
    limit = limits.get("max_executions_per_day")
    day = timezone.localdate()
    with transaction.atomic():
        row, _created = DailyExecution.objects.select_for_update().get_or_create(
            user=user, day=day, defaults={"count": 0}
        )
        if limit is not None and int(row.count) >= int(limit):
            raise DomainError(
                "Ya usaste las ejecuciones de hoy.", code="plan_limit", status_code=403
            )
        row.count += 1
        row.save(update_fields=["count"])
    remaining = None if limit is None else max(0, int(limit) - int(row.count))
    return {"limit": None if limit is None else int(limit), "used": row.count, "remaining": remaining}


def gate_request(request) -> None:
    """Cierra la API de la aplicación cuando el navegador no está permitido."""
    path = request.path
    if (
        not path.startswith("/api/v1/")
        or path.startswith("/api/v1/auth/")
        or path.startswith("/api/v1/billing/")
    ):
        return
    user = getattr(request, "user", None)
    if not isinstance(user, User) or not user.is_authenticated:
        return
    if user.profile.role == Profile.ADMIN:
        raise DomainError(
            "Esta cuenta administra los niveles.", code="admin_account", status_code=403
        )
    snapshot = account_access(user)
    access = snapshot["access"]
    assert isinstance(access, dict)
    if not access["browser_app"] and not client_is_desktop(request):
        raise DomainError(
            "Esta función solo está disponible en la aplicación.",
            code="browser_forbidden",
            status_code=403,
        )
    needed = _feature_for(path)
    if needed is None:
        return
    features = access["features"]
    assert isinstance(features, dict)
    if not any(features.get(key) is True for key in needed):
        raise DomainError(
            "Tu nivel no incluye esta función.", code="plan_forbidden", status_code=403
        )


def _feature_for(path: str) -> tuple[str, ...] | None:
    if "/flowchart/" in path:
        return ("diagram",)
    if "/validate/" in path:
        return ("validate",)
    if "/translate/" in path:
        return ("translate",)
    if "/debug/" in path:
        return ("debug",)
    if path.startswith("/api/v1/usage/"):
        return ("execute", "languages")
    if "/execute/" in path:
        return ("execute",)
    if path.startswith("/api/v1/languages/"):
        return ("languages",)
    if path.startswith("/api/v1/executions/"):
        return ("execute", "debug")
    if path.startswith(("/api/v1/communities/", "/api/v1/people/", "/api/v1/classroom/")):
        return ("communities",)
    if path.startswith(
        ("/api/v1/learning/bank", "/api/v1/learning/challenges/csv", "/api/v1/learning/catalog")
    ):
        return ("lab_bank", "lab_routes")
    if path.startswith("/api/v1/learning/authored"):
        return ("lab_routes",)
    if path.startswith("/api/v1/learning/roster"):
        return ("lab_progress",)
    if path.startswith("/api/v1/learning/practices"):
        return ("lab_practice",)
    if path.startswith(
        ("/api/v1/learning/preview", "/api/v1/learning/import", "/api/v1/learning/run")
    ):
        return ("lab",)
    if path.startswith("/api/v1/learning/"):
        return ("lab_route",)
    if path.startswith(
        (
            "/api/v1/projects",
            "/api/v1/folders",
            "/api/v1/algorithms",
            "/api/v1/share-links",
            "/api/v1/shared/",
        )
    ):
        return ("editor", "compose")
    return None


def catalog_payload() -> list[dict[str, object]]:
    return [
        {"key": item.key, "label": item.label, "audiences": sorted(item.audiences)}
        for item in FEATURES
    ]


def plan_payload(plan: Plan) -> dict[str, object]:
    return {
        "id": str(plan.id),
        "code": plan.code,
        "name": plan.name,
        "audience": plan.audience,
        "price_cents": plan.price_cents,
        "currency": plan.currency,
        "period_days": plan.period_days,
        "browser_allowed": plan.browser_allowed,
        "max_projects": plan.max_projects,
        "max_algorithms": plan.max_algorithms,
        "max_executions_per_day": plan.max_executions_per_day,
        "features": _features_of(plan),
        "is_default": plan.is_default,
        "is_active": plan.is_active,
        "sort_order": plan.sort_order,
    }


def _optional_limit(value: object, field: str) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DomainError(f"{field} no es válido.")
    return value


def _execution_limit(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < MIN_DAILY_RUNS:
        raise DomainError("El tope de ejecuciones es 3 o más, o sin límite.")
    return value


def _money(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DomainError("El precio no es válido.")
    return value


def _days(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 3650:
        raise DomainError("Los días de vigencia no son válidos.")
    return value


def _currency(value: object) -> str:
    if not isinstance(value, str) or len(value.strip()) != 3 or not value.isalpha():
        raise DomainError("La moneda no es válida.")
    return value.strip().upper()


def _code(value: object) -> str:
    if not isinstance(value, str) or not _CODE.fullmatch(value.strip()):
        raise DomainError("El código del nivel no es válido.")
    return value.strip()


def _audience(value: object) -> str:
    if value not in (Plan.STUDENT, Plan.TEACHER):
        raise DomainError("El nivel es de alumno o de docente.")
    return value


def _name(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 80:
        raise DomainError("El nombre del nivel no es válido.")
    return value.strip()


def create_plan(data: dict) -> Plan:
    audience = _audience(data.get("audience"))
    last = Plan.objects.filter(audience=audience).order_by("-sort_order").first()
    plan = Plan(
        code=_code(data.get("code")),
        name=_name(data.get("name")),
        audience=audience,
        price_cents=_money(data.get("price_cents", 0)),
        currency=_currency(data.get("currency", "MXN")),
        period_days=_days(data.get("period_days", 0)),
        browser_allowed=data.get("browser_allowed") is True,
        max_projects=_optional_limit(data.get("max_projects"), "El tope de proyectos"),
        max_algorithms=_optional_limit(data.get("max_algorithms"), "El tope de algoritmos"),
        max_executions_per_day=(
            _execution_limit(data.get("max_executions_per_day"))
            if "max_executions_per_day" in data
            else MIN_DAILY_RUNS
        ),
        features=normalize_features(audience, data.get("features", {})),
        is_default=False,
        is_active=data.get("is_active", True) is not False,
        sort_order=0 if last is None else last.sort_order + 1,
    )
    plan.save()
    return plan


def update_plan(plan: Plan, data: dict) -> Plan:
    if "name" in data:
        plan.name = _name(data.get("name"))
    if "price_cents" in data:
        plan.price_cents = _money(data.get("price_cents"))
    if "currency" in data:
        plan.currency = _currency(data.get("currency"))
    if "period_days" in data:
        plan.period_days = _days(data.get("period_days"))
    if "browser_allowed" in data:
        if not isinstance(data.get("browser_allowed"), bool):
            raise DomainError("Indica si el navegador queda permitido.")
        plan.browser_allowed = data["browser_allowed"]
    if "max_projects" in data:
        plan.max_projects = _optional_limit(data.get("max_projects"), "El tope de proyectos")
    if "max_algorithms" in data:
        plan.max_algorithms = _optional_limit(data.get("max_algorithms"), "El tope de algoritmos")
    if "max_executions_per_day" in data:
        plan.max_executions_per_day = _execution_limit(data.get("max_executions_per_day"))
    if "features" in data:
        plan.features = normalize_features(plan.audience, data.get("features"))
    if "is_active" in data:
        if not isinstance(data.get("is_active"), bool):
            raise DomainError("Indica si el nivel sigue disponible.")
        if plan.is_default and data["is_active"] is False:
            raise DomainError("El nivel de alta no se puede desactivar.")
        plan.is_active = data["is_active"]
    plan.save()
    return plan


def _parse_until(value: object):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise DomainError("La fecha de pago no es válida.")
    parsed = parse_datetime(value)
    if parsed is None:
        raise DomainError("La fecha de pago no es válida.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def assign_plan(user: User, data: dict) -> Subscription:
    if user.profile.role == Profile.ADMIN:
        raise DomainError("El administrador no tiene un nivel de alumno o docente.")
    subscription = Subscription.objects.filter(user=user).select_related("plan").first()
    if "plan_id" in data:
        plan_id = data.get("plan_id")
        try:
            plan = Plan.objects.get(pk=plan_id, is_active=True)
        except (Plan.DoesNotExist, ValueError, TypeError) as exc:
            raise DomainError(
                "Ese nivel no está disponible.", code="not_found", status_code=404
            ) from exc
        if plan.audience != user.profile.role:
            raise DomainError("Ese nivel es de otro tipo de cuenta.")
        if subscription is None:
            subscription = Subscription(user=user, plan=plan)
        subscription.plan = plan
        if "paid_until" in data:
            subscription.paid_until = _parse_until(data.get("paid_until"))
        elif plan.period_days:
            subscription.paid_until = timezone.now() + timedelta(days=plan.period_days)
        else:
            subscription.paid_until = None
    elif subscription is None:
        raise DomainError("Esta cuenta no tiene un nivel.")
    if "browser_allowed" in data:
        choice = data.get("browser_allowed")
        if choice is not None and not isinstance(choice, bool):
            raise DomainError("El acceso por navegador no es válido.")
        subscription.browser_allowed = choice
    subscription.save()
    return subscription


def user_row(user: User) -> dict[str, object]:
    snapshot = account_access(user)
    plan = snapshot["plan"]
    override = None
    if user.profile.role != Profile.ADMIN:
        override = user.subscription.browser_allowed
    return {
        "id": user.pk,
        "email": user.email,
        "display_name": user.profile.display_name,
        "role": user.profile.role,
        "plan": plan,
        "browser_allowed": override,
    }
