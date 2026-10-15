"""Los errores de la API salen con un mismo sobre."""

from typing import Any

from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler

from config.errors import DomainError


class TrazaError(Exception):
    """Puente hacia el manejador de DRF."""

    def __init__(self, message: str, *, code: str, status_code: int) -> None:
        super().__init__(message)
        from rest_framework.exceptions import APIException

        self.api = APIException(detail=message, code=code)
        self.api.status_code = status_code


def traza_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DomainError):
        bridge = TrazaError(exc.message, code=exc.code, status_code=exc.status_code)
        exc = bridge.api
    response = exception_handler(exc, context)
    if response is None:
        return None
    code = "invalid"
    if hasattr(exc, "get_codes"):
        codes = exc.get_codes()
        if isinstance(codes, str):
            code = codes
    detail = getattr(exc, "detail", None)
    message = "No se pudo completar la solicitud."
    details = _flatten(detail)
    if isinstance(detail, str):
        message = detail
    elif details:
        message = details[0]
    if isinstance(exc, NotAuthenticated):
        code = "not_authenticated"
        message = "Inicia sesión para continuar."
    elif isinstance(exc, PermissionDenied):
        text = str(detail)
        if "CSRF" in text:
            code = "csrf_failed"
            message = "Falta el token CSRF o no es válido."
        else:
            code = "permission_denied"
            message = text
    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response


def _flatten(detail: object, prefix: str = "") -> list[str]:
    if isinstance(detail, dict):
        rows: list[str] = []
        for key, value in detail.items():
            rows.extend(_flatten(value, str(key)))
        return rows
    if isinstance(detail, list):
        rows = []
        for item in detail:
            rows.extend(_flatten(item, prefix))
        return rows
    if detail is None:
        return []
    text = str(detail)
    return [f"{prefix}: {text}" if prefix else text]
