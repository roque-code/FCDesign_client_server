"""Cierra la sesión cuando la cuenta lleva un rato sin usarse."""

from django.contrib.auth import logout
from django.http import JsonResponse

from apps.accounts.guard import release_session, session_idle_message, session_is_idle, touch_session
from apps.accounts.models import User


class IdleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if isinstance(user, User) and user.is_authenticated:
            if session_is_idle(request.session):
                release_session(user, request.session.session_key)
                logout(request)
                if request.path.startswith("/api/"):
                    return JsonResponse(
                        {
                            "error": {
                                "code": "session_idle",
                                "message": session_idle_message(),
                                "details": [],
                            }
                        },
                        status=401,
                    )
            else:
                touch_session(request.session)
        return self.get_response(request)
