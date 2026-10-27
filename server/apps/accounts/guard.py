"""Una sesión por cuenta, cierre por inactividad y bloqueo tras intentos fallidos."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from importlib import import_module

from django.conf import settings
from django.contrib.auth import login
from django.core.cache import cache
from django.db import transaction

from apps.accounts.models import User
from config.errors import DomainError

_BACKEND = "django.contrib.auth.backends.ModelBackend"
_LOCK_MESSAGE = "Demasiados intentos. Espera 15 minutos para volver a entrar."
_OPEN_MESSAGE = (
    "Ya hay una sesión abierta en otro equipo. Ciérrala ahí o espera 30 minutos sin usarla."
)
_IDLE_MESSAGE = "La sesión se cerró por inactividad. Vuelve a entrar."
_WINDOW_SECONDS = 25
_WINDOW_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")


def session_idle_message() -> str:
    return _IDLE_MESSAGE


def session_open_message() -> str:
    return _OPEN_MESSAGE


def refuse_locked_login(email: str) -> None:
    if cache.get(_lock_key(email)):
        raise DomainError(_LOCK_MESSAGE, code="login_locked", status_code=429)


def note_login_failure(email: str) -> None:
    """Cuenta el fallo. Al tercero bloquea ese correo durante 15 minutos."""
    key = _fail_key(email)
    window = int(settings.LOGIN_LOCK_SECONDS)
    if cache.add(key, 1, timeout=window):
        count = 1
    else:
        try:
            count = int(cache.incr(key))
        except ValueError:
            cache.set(key, 1, timeout=window)
            count = 1
    if count >= int(settings.LOGIN_FAILURE_LIMIT):
        cache.set(_lock_key(email), 1, timeout=window)
        cache.delete(key)
        raise DomainError(_LOCK_MESSAGE, code="login_locked", status_code=429)


def clear_login_failures(email: str) -> None:
    cache.delete(_fail_key(email))
    cache.delete(_lock_key(email))


def begin_session(request, user: User) -> User:
    """Abre la única sesión de la cuenta. Rechaza otra máquina o la aplicación si ya hay una."""
    with transaction.atomic():
        current = User.objects.select_for_update().get(pk=user.pk)
        if _elsewhere(current, request):
            raise DomainError(_OPEN_MESSAGE, code="session_open", status_code=409)
        sent = sent_window(request)
        if window_blocks(request.session, sent):
            raise DomainError(_OPEN_MESSAGE, code="session_open", status_code=409)
        login(request, current, backend=_BACKEND)
        now = int(time.time())
        request.session["last_activity"] = now
        request.session["session_started"] = now
        remember_window(request.session, sent)
        request.session.save()
        current.session_key = request.session.session_key or ""
        current.save(update_fields=["session_key"])
    return current


def hold_active_session(user: User, request) -> bool:
    """La petición es la sesión vigente. Otra cookie abierta no la sustituye."""
    current_key = request.session.session_key or ""
    if not current_key or user.session_key == current_key:
        return True
    with transaction.atomic():
        locked = User.objects.select_for_update().get(pk=user.pk)
        if locked.session_key == current_key:
            user.session_key = current_key
            return True
        if locked.session_key and _store(locked.session_key).exists(locked.session_key):
            return False
        locked.session_key = current_key
        locked.save(update_fields=["session_key"])
    user.session_key = current_key
    return True


def sent_window(request) -> str:
    raw = request.headers.get("X-Traza-Window", "")
    if not isinstance(raw, str):
        return ""
    cleaned = raw.strip()
    if len(cleaned) < 8 or len(cleaned) > 64:
        return ""
    if any(char not in _WINDOW_CHARS for char in cleaned):
        return ""
    return cleaned


def window_blocks(session, sent: str) -> bool:
    """Otra ventana del mismo navegador sigue usando esta cookie."""
    if not sent:
        return False
    stored = session.get("window_id")
    if not isinstance(stored, str) or not stored or stored == sent:
        return False
    seen = session.get("window_seen")
    if not isinstance(seen, int):
        return True
    return int(time.time()) - seen < _WINDOW_SECONDS


def remember_window(session, sent: str) -> None:
    if not sent:
        return
    session["window_id"] = sent
    session["window_seen"] = int(time.time())


def release_session(user: User, session_key: str | None) -> None:
    if not session_key:
        return
    User.objects.filter(pk=user.pk, session_key=session_key).update(session_key="")


def session_is_idle(session) -> bool:
    last = session.get("last_activity")
    if not isinstance(last, int):
        return False
    return int(time.time()) - last >= int(settings.SESSION_IDLE_SECONDS)


def touch_session(session) -> None:
    now = int(time.time())
    session["last_activity"] = now
    if not isinstance(session.get("session_started"), int):
        session["session_started"] = now


def close_account_session(user: User) -> None:
    """Cierra la sesión abierta para que la cuenta deje de estar conectada."""
    key = user.session_key
    if key:
        _store(key).delete()
    if user.session_key:
        User.objects.filter(pk=user.pk).update(session_key="")
        user.session_key = ""


def active_sessions() -> list[dict[str, object]]:
    """Cuentas cuya sesión sigue abierta y no venció por inactividad."""
    now = int(time.time())
    idle = int(settings.SESSION_IDLE_SECONDS)
    rows: list[dict[str, object]] = []
    people = (
        User.objects.select_related("profile")
        .exclude(session_key="")
        .order_by("email")
    )
    for user in people:
        store = _store(user.session_key)
        if not store.exists(user.session_key):
            continue
        last = store.get("last_activity")
        if isinstance(last, int) and now - last >= idle:
            continue
        started = store.get("session_started")
        if not isinstance(started, int):
            started = last if isinstance(last, int) else now
        seconds = max(0, now - started)
        profile = user.profile
        rows.append(
            {
                "id": user.pk,
                "email": user.email,
                "display_name": profile.display_name,
                "role": profile.role,
                "seconds": seconds,
                "started_at": datetime.fromtimestamp(started, UTC).isoformat(),
            }
        )
    rows.sort(key=lambda row: (-int(row["seconds"]), str(row["display_name"]).casefold()))
    return rows


def _elsewhere(user: User, request) -> bool:
    key = user.session_key
    if not key or key == request.session.session_key:
        return False
    store = _store(key)
    if not store.exists(key):
        return False
    last = store.get("last_activity")
    if isinstance(last, int) and int(time.time()) - last >= int(settings.SESSION_IDLE_SECONDS):
        store.delete()
        return False
    return True


def _store(session_key: str):
    engine = import_module(settings.SESSION_ENGINE)
    return engine.SessionStore(session_key=session_key)


def _fail_key(email: str) -> str:
    return f"auth.fail:{email}"


def _lock_key(email: str) -> str:
    return f"auth.lock:{email}"
