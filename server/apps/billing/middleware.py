"""Cierra la aplicación en el navegador cuando el nivel no lo permite.

La cuenta y el administrador siguen abiertos. No agrega una petición: usa la
sesión que la vista ya iba a leer.
"""

from django.http import JsonResponse

from config.errors import DomainError


class PlanGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/v1/") and not request.path.startswith(
            ("/api/v1/auth/", "/api/v1/billing/")
        ):
            from apps.billing.services import gate_request

            try:
                gate_request(request)
            except DomainError as exc:
                return JsonResponse(
                    {"error": {"code": exc.code, "message": exc.message, "details": []}},
                    status=exc.status_code,
                )
        return self.get_response(request)
