"""Ayudas pequeñas de las vistas."""

from typing import Any

from rest_framework.request import Request

from apps.accounts.models import User
from config.errors import DomainError


def current_user(request: Request) -> User:
    user = request.user
    if not isinstance(user, User):
        raise DomainError(
            "Inicia sesión para continuar.",
            code="not_authenticated",
            status_code=403,
        )
    return user


def client_ip(request) -> str | None:
    address = request.META.get("REMOTE_ADDR")
    return address if isinstance(address, str) and address else None


def object_body(data: object) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise DomainError("El cuerpo debe ser un objeto JSON.")
    return data
