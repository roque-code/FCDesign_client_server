"""Cabeceras y CSRF de la API.

DRF marca sus vistas como exentas y solo comprueba el token cuando ya hay
sesión. El alta y el inicio de sesión también deben exigirlo.
"""

from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.deprecation import MiddlewareMixin

_SAFE = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Content-Security-Policy"] = "default-src 'self'"
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "private, no-store"
            response["Vary"] = "Cookie"
        return response


class ApiCsrfMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        self.csrf = CsrfViewMiddleware(get_response)

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if not request.path.startswith("/api/"):
            return None
        if request.method in _SAFE or getattr(request, "_dont_enforce_csrf_checks", False):
            return None
        was_exempt = getattr(callback, "csrf_exempt", False)
        callback.csrf_exempt = False
        try:
            rejected = self.csrf.process_view(request, callback, callback_args, callback_kwargs)
        finally:
            callback.csrf_exempt = was_exempt
        if rejected is None:
            return None
        return JsonResponse(
            {
                "error": {
                    "code": "csrf_failed",
                    "message": "Falta el token CSRF o no es válido.",
                    "details": [],
                }
            },
            status=403,
        )
