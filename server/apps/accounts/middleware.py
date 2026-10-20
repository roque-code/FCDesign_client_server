"""Cierra la sesión cuando la cuenta lleva un rato sin usarse."""

from django.contrib.auth import logout
from django.http import JsonResponse

from apps.accounts.guard import (
    hold_active_session,
    release_session,
    remember_window,
    sent_window,
    session_idle_message,
    session_is_idle,
    session_open_message,
    touch_session,
    window_blocks,
)
from apps.accounts.models import User


class IdleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if isinstance(user, User) and user.is_authenticated:
            window = sent_window(request)
            if not hold_active_session(user, request):
                logout(request)
                denied = _api_closed(request, "session_open", session_open_message())
                if denied is not None:
                    return denied
            elif window_blocks(request.session, window):
                denied = _api_closed(request, "session_open", session_open_message())
                if denied is not None:
                    return denied
            elif session_is_idle(request.session):
                release_session(user, request.session.session_key)
                logout(request)
                denied = _api_closed(request, "session_idle", session_idle_message())
                if denied is not None:
                    return denied
            else:
                if request.headers.get("X-Traza-Presence") != "1":
                    touch_session(request.session)
                remember_window(request.session, window)
        return self.get_response(request)


def _api_closed(request, code: str, message: str) -> JsonResponse | None:
    if not request.path.startswith("/api/"):
        return None
    return JsonResponse(
        {"error": {"code": code, "message": message, "details": []}},
        status=401,
    )
