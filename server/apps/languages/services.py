from __future__ import annotations

from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.accounts.services import clean_label
from apps.languages.models import LANGUAGES, LanguageProgram
from config.errors import DomainError

MAX_SOURCE = 256 * 1024
MAX_PROGRAMS = 300


def program_payload(program: LanguageProgram, *, with_source: bool = True) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": str(program.id),
        "name": program.name,
        "language": program.language,
        "updated_at": program.updated_at.isoformat(),
    }
    if with_source:
        payload["source"] = program.source
    return payload


def _language(value: object) -> str:
    if not isinstance(value, str) or value not in LANGUAGES:
        raise DomainError("Ese lenguaje no está en la lista.")
    return value


def _source(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise DomainError("El código no es válido.")
    if len(value) > MAX_SOURCE:
        raise DomainError("El código es demasiado grande.")
    return value


def _name(value: object) -> str:
    return clean_label(value, field="el nombre del programa", limit=120, required=True)


def _taken() -> DomainError:
    return DomainError(
        "Ya tienes un programa con ese nombre en este lenguaje.", code="conflict", status_code=409
    )


def list_programs(user: User) -> list[dict[str, object]]:
    rows = user.language_programs.order_by("language", "name")
    return [program_payload(item, with_source=False) for item in rows]


def get_program(user: User, program_id) -> LanguageProgram:
    found = LanguageProgram.objects.filter(owner=user, pk=program_id).first()
    if found is None:
        raise DomainError("No se encontró el programa.", code="not_found", status_code=404)
    return found


def create_program(user: User, data: dict) -> LanguageProgram:
    language = _language(data.get("language"))
    name = _name(data.get("name"))
    source = _source(data.get("source"))
    if user.language_programs.count() >= MAX_PROGRAMS:
        raise DomainError(
            "Llegaste al máximo de programas guardados.", code="plan_limit", status_code=403
        )
    try:
        with transaction.atomic():
            return LanguageProgram.objects.create(
                owner=user, name=name, language=language, source=source
            )
    except IntegrityError as exc:
        raise _taken() from exc


def update_program(program: LanguageProgram, data: dict) -> LanguageProgram:
    fields: list[str] = []
    if "name" in data:
        program.name = _name(data.get("name"))
        fields.append("name")
    if "source" in data:
        program.source = _source(data.get("source"))
        fields.append("source")
    if not fields:
        return program
    try:
        with transaction.atomic():
            program.save(update_fields=[*fields, "updated_at"])
    except IntegrityError as exc:
        raise _taken() from exc
    return program


def student_programs(teacher: User, user_id: int) -> dict[str, object]:
    from apps.classroom.services import person_payload, require_teacher, teacher_has_student

    require_teacher(teacher)
    if not teacher_has_student(teacher, user_id):
        raise DomainError("No se encontró al alumno.", code="not_found", status_code=404)
    student = User.objects.select_related("profile").get(pk=user_id)
    rows = student.language_programs.order_by("language", "name")
    return {
        "student": person_payload(student),
        "programs": [program_payload(item) for item in rows],
    }
