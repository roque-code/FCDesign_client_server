"""Una sesión por cuenta, cierre por inactividad y bloqueo tras intentos fallidos."""

from __future__ import annotations

import time
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


def session_idle_message() -> str:
    return _IDLE_MESSAGE


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
        login(request, current, backend=_BACKEND)
        request.session["last_activity"] = int(time.time())
        request.session.save()
        current.session_key = request.session.session_key or ""
        current.save(update_fields=["session_key"])
    return current


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
    session["last_activity"] = int(time.time())


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
