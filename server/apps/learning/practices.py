"""Guardar, abrir y borrar una práctica libre. No toca los algoritmos del editor."""

from __future__ import annotations

import unicodedata
from typing import Any

from django.db import IntegrityError, transaction

from apps.learning.models import Practice
from apps.learning.services import load_workspace
from config.errors import DomainError
from language_core.block_adapter import adapt_workspace

MAX_PRACTICES = 40


def list_practices(user) -> dict[str, object]:
    rows = Practice.objects.filter(user=user).order_by("-updated_at", "name")
    return {"results": [_summary(item) for item in rows]}


def create_practice(user, data: dict[str, Any]) -> dict[str, object]:
    if Practice.objects.filter(user=user).count() >= MAX_PRACTICES:
        raise DomainError(
            "Ya guardaste el máximo de prácticas.",
            code="conflict",
            status_code=409,
        )
    name = _clean_name(data.get("name"))
    workspace = load_workspace(data)
    try:
        with transaction.atomic():
            practice = Practice.objects.create(
                user=user,
                name=name,
                workspace=workspace,
                source=adapt_workspace(workspace).source,
            )
    except IntegrityError as exc:
        raise DomainError(
            "Ya tienes una práctica con ese nombre.",
            code="conflict",
            status_code=409,
        ) from exc
    return _detail(practice)


def get_practice(user, practice_id) -> dict[str, object]:
    return _detail(_owned(user, practice_id))


def update_practice(user, practice_id, data: dict[str, Any]) -> dict[str, object]:
    practice = _owned(user, practice_id)
    if "name" in data:
        practice.name = _clean_name(data.get("name"))
    if "workspace" in data:
        workspace = load_workspace(data)
        practice.workspace = workspace
        practice.source = adapt_workspace(workspace).source
    if "name" not in data and "workspace" not in data:
        raise DomainError("No hay cambios para guardar.")
    try:
        with transaction.atomic():
            practice.save()
    except IntegrityError as exc:
        raise DomainError(
            "Ya tienes una práctica con ese nombre.",
            code="conflict",
            status_code=409,
        ) from exc
    return _detail(practice)


def delete_practice(user, practice_id) -> None:
    _owned(user, practice_id).delete()


def _owned(user, practice_id) -> Practice:
    try:
        return Practice.objects.get(pk=practice_id, user=user)
    except Practice.DoesNotExist as exc:
        raise DomainError(
            "No se encontró la práctica.",
            code="not_found",
            status_code=404,
        ) from exc


def _clean_name(value: object) -> str:
    if not isinstance(value, str):
        raise DomainError("El nombre no es válido.")
    name = value.strip()
    if not name:
        raise DomainError("El nombre no puede estar vacío.")
    if len(name) > 120:
        raise DomainError("El nombre admite hasta 120 caracteres.")
    if any(unicodedata.category(character) == "Cc" for character in name):
        raise DomainError("El nombre contiene caracteres de control.")
    return name


def _summary(practice: Practice) -> dict[str, object]:
    return {
        "id": str(practice.id),
        "name": practice.name,
        "source": practice.source,
        "updated_at": practice.updated_at.isoformat(),
    }


def _detail(practice: Practice) -> dict[str, object]:
    body = _summary(practice)
    body["workspace"] = practice.workspace
    return body
