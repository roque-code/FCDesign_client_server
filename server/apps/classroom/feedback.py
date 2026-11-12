"""Calificación y comentario del docente sobre los ejercicios de sus alumnos."""

from __future__ import annotations

import csv
import io
import math
import unicodedata
import uuid
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record
from apps.classroom.focus import (
    apply_event,
    away_text,
    focus_event,
    focus_report,
    focus_start,
    watching,
)
from apps.classroom.models import Community, ExerciseFeedback, ExerciseFocus
from apps.classroom.services import (
    NOT_FOUND,
    classroom_students,
    focus_rules,
    require_teacher,
    teacher_has_student,
)
from apps.languages.models import LanguageProgram
from apps.projects.models import Algorithm
from config.errors import DomainError

MAX_COMMENT = 2000
FEEDBACK_PAGE = 10
MAX_FEEDBACK_PAGE = 50
LANGUAGE_LABELS = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "java": "Java",
    "c": "C",
    "cpp": "C++",
    "csharp": "C#",
}
_LABELS = {
    "es": {
        "name": "Nombre",
        "email": "Correo",
        "communities": "Comunidades",
        "kind": "Tipo",
        "context": "Proyecto o lenguaje",
        "exercise": "Ejercicio",
        "grade": "Calificación",
        "comment": "Comentario",
        "graded_at": "Fecha de la calificación",
        "exits": "Salidas",
        "away": "Tiempo fuera",
        "algorithm": "Pseudocódigo",
        "program": "Lenguaje",
    },
    "en": {
        "name": "Name",
        "email": "Email",
        "communities": "Communities",
        "kind": "Type",
        "context": "Project or language",
        "exercise": "Exercise",
        "grade": "Grade",
        "comment": "Comment",
        "graded_at": "Graded on",
        "exits": "Exits",
        "away": "Time away",
        "algorithm": "Pseudocode",
        "program": "Language",
    },
}


def _missing() -> DomainError:
    return DomainError("No se encontró el ejercicio.", code=NOT_FOUND, status_code=404)


def _exercise(kind: str, exercise_id) -> Algorithm | LanguageProgram:
    if kind == ExerciseFeedback.ALGORITHM:
        found = (
            Algorithm.objects.select_related("project")
            .filter(pk=exercise_id, project__deleted_at__isnull=True)
            .first()
        )
    elif kind == ExerciseFeedback.PROGRAM:
        found = LanguageProgram.objects.filter(pk=exercise_id).first()
    else:
        raise DomainError("Ese tipo de ejercicio no existe.")
    if found is None:
        raise _missing()
    return found


def _for_teacher(teacher: User, kind: str, exercise_id) -> Algorithm | LanguageProgram:
    require_teacher(teacher)
    exercise = _exercise(kind, exercise_id)
    if not teacher_has_student(teacher, exercise.owner_id):
        raise _missing()
    return exercise


def _grade(value: object) -> Decimal | None:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise DomainError("La calificación debe ser un número de 0 a 100.")
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation as exc:
        raise DomainError("La calificación debe ser un número de 0 a 100.") from exc
    if not number.is_finite() or number < 0 or number > 100:
        raise DomainError("La calificación debe ser un número de 0 a 100.")
    if number != number.quantize(Decimal("0.01")):
        raise DomainError("La calificación admite hasta dos decimales.")
    return number.quantize(Decimal("0.01"))


def _comment(value: object) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise DomainError("El comentario no es válido.")
    text = value.strip()
    if len(text) > MAX_COMMENT:
        raise DomainError(f"El comentario admite hasta {MAX_COMMENT} caracteres.")
    if any(ord(char) < 32 and char not in "\n\t" for char in text):
        raise DomainError("El comentario contiene caracteres de control.")
    return text


def grade_text(grade: Decimal | None) -> str:
    if grade is None:
        return ""
    return format(grade.normalize(), "f")


def feedback_payload(item: ExerciseFeedback) -> dict[str, object]:
    if item.algorithm_id:
        kind = ExerciseFeedback.ALGORITHM
        exercise_id = item.algorithm_id
        name = item.algorithm.name
        context = item.algorithm.project.name
    else:
        kind = ExerciseFeedback.PROGRAM
        exercise_id = item.program_id
        name = item.program.name
        context = LANGUAGE_LABELS.get(item.program.language, item.program.language)
    return {
        "id": str(item.id),
        "kind": kind,
        "exercise_id": str(exercise_id),
        "exercise_name": name,
        "context": context,
        "grade": float(item.grade) if item.grade is not None else None,
        "comment": item.comment,
        "teacher": {"id": item.teacher_id, "display_name": item.teacher.profile.display_name},
        "student_id": item.student_id,
        "updated_at": item.updated_at.isoformat(),
    }


def _query():
    return ExerciseFeedback.objects.select_related(
        "teacher__profile", "algorithm__project", "program"
    )


def _lookup(kind: str, exercise) -> dict[str, object]:
    return {"algorithm": exercise} if kind == ExerciseFeedback.ALGORITHM else {"program": exercise}


def teacher_feedback(teacher: User, kind: str, exercise_id) -> dict[str, object] | None:
    exercise = _for_teacher(teacher, kind, exercise_id)
    found = _query().filter(teacher=teacher, **_lookup(kind, exercise)).first()
    return feedback_payload(found) if found else None


def _focus_summary(log: ExerciseFocus | None) -> dict[str, object] | None:
    if log is None:
        return None
    report = focus_report(log.focus, None)
    if report is not None:
        # Una salida sin regreso puede ser un navegador cerrado; no se presenta como ausencia viva.
        report["away_now"] = False
    return report


def teacher_focus(teacher: User, kind: str, exercise_id) -> dict[str, object] | None:
    exercise = _for_teacher(teacher, kind, exercise_id)
    return _focus_summary(ExerciseFocus.objects.filter(**_lookup(kind, exercise)).first())


def exercise_focus(student: User, kind: str, exercise_id, data: dict) -> dict[str, object] | None:
    """Salidas del alumno en su propio ejercicio. Sin vigilancia no se registra nada."""
    event, reason = focus_event(data, ("open",))
    exercise = _exercise(kind, exercise_id)
    if exercise.owner_id != student.pk:
        raise _missing()
    if not focus_rules(student)["watched"]:
        return None
    with transaction.atomic():
        log, _created = ExerciseFocus.objects.select_for_update().get_or_create(
            student=student, **_lookup(kind, exercise)
        )
        current = log.focus if watching(log.focus) else focus_start({"watched": True})
        log.focus, _reached = apply_event(current, event, reason, timezone.now())
        log.save(update_fields=["focus", "updated_at"])
    return _focus_summary(log)


@transaction.atomic
def save_feedback(
    teacher: User, kind: str, exercise_id, data: dict, ip_address: str | None = None
) -> dict[str, object] | None:
    exercise = _for_teacher(teacher, kind, exercise_id)
    grade = _grade(data.get("grade"))
    comment = _comment(data.get("comment"))
    lookup = _lookup(kind, exercise)
    if grade is None and comment == "":
        ExerciseFeedback.objects.filter(teacher=teacher, **lookup).delete()
        saved = None
    else:
        saved, _created = ExerciseFeedback.objects.update_or_create(
            teacher=teacher,
            **lookup,
            defaults={"student_id": exercise.owner_id, "grade": grade, "comment": comment},
        )
    record(
        "feedback.saved" if saved else "feedback.cleared",
        actor=teacher,
        object_type=kind,
        object_id=str(exercise.pk),
        metadata={"student_id": exercise.owner_id, "grade": grade_text(grade)},
        ip_address=ip_address,
    )
    if saved is None:
        return None
    return feedback_payload(_query().get(pk=saved.pk))


def _whole_number(value: object, default: int, *, low: int, high: int, message: str) -> int:
    if value is None or value == "":
        return default
    try:
        number = int(str(value))
    except ValueError as exc:
        raise DomainError(message) from exc
    if number < low or number > high:
        raise DomainError(message)
    return number


def received_feedback(
    student: User, params: Mapping[str, object] | None = None
) -> dict[str, object]:
    params = params or {}
    kind = str(params.get("kind") or "")
    language = str(params.get("language") or "")
    exercise = str(params.get("exercise") or "")
    if kind not in ("", ExerciseFeedback.ALGORITHM, ExerciseFeedback.PROGRAM):
        raise DomainError("Ese tipo de ejercicio no existe.")
    if language and language not in LANGUAGE_LABELS:
        raise DomainError("Ese lenguaje no existe.")
    if language:
        kind = ExerciseFeedback.PROGRAM
    page = _whole_number(
        params.get("page"), 1, low=1, high=100_000, message="La página no es válida."
    )
    size = _whole_number(
        params.get("page_size"),
        FEEDBACK_PAGE,
        low=1,
        high=MAX_FEEDBACK_PAGE,
        message=f"Cada página admite de 1 a {MAX_FEEDBACK_PAGE} calificaciones.",
    )

    visible = ExerciseFeedback.objects.filter(student=student).filter(
        Q(algorithm__isnull=True)
        | Q(algorithm__deleted_at__isnull=True, algorithm__project__deleted_at__isnull=True)
    )
    totals = {
        "all": visible.count(),
        ExerciseFeedback.ALGORITHM: visible.filter(algorithm__isnull=False).count(),
        ExerciseFeedback.PROGRAM: visible.filter(program__isnull=False).count(),
    }
    languages = [
        {
            "code": row["program__language"],
            "label": LANGUAGE_LABELS.get(row["program__language"], row["program__language"]),
            "count": row["count"],
        }
        for row in visible.filter(program__isnull=False)
        .values("program__language")
        .annotate(count=Count("id"))
        .order_by("program__language")
    ]

    chosen = visible
    if kind == ExerciseFeedback.ALGORITHM:
        chosen = chosen.filter(algorithm__isnull=False)
    elif kind == ExerciseFeedback.PROGRAM:
        chosen = chosen.filter(program__isnull=False)
    if language:
        chosen = chosen.filter(program__language=language)
    if exercise:
        try:
            exercise_id = uuid.UUID(exercise)
        except ValueError as exc:
            raise _missing() from exc
        chosen = chosen.filter(Q(algorithm_id=exercise_id) | Q(program_id=exercise_id))

    count = chosen.count()
    pages = max(1, math.ceil(count / size))
    page = min(page, pages)
    average = chosen.aggregate(value=Avg("grade"))["value"]
    rows = chosen.select_related("teacher__profile", "algorithm__project", "program").order_by(
        "-updated_at", "id"
    )[(page - 1) * size : page * size]
    return {
        "results": [feedback_payload(item) for item in rows],
        "count": count,
        "page": page,
        "pages": pages,
        "page_size": size,
        "average": round(float(average), 2) if average is not None else None,
        "totals": totals,
        "languages": languages,
    }


def grades_csv(teacher: User, community: str, lang: str) -> tuple[str, str]:
    require_teacher(teacher)
    labels = _LABELS["en" if lang == "en" else "es"]
    chosen = community.strip()
    if chosen and not Community.objects.filter(owner=teacher, name=chosen).exists():
        raise DomainError("No se encontró la comunidad.", code=NOT_FOUND, status_code=404)
    students = [
        row for row in classroom_students(teacher) if chosen == "" or chosen in row["communities"]
    ]
    ids = [row["id"] for row in students]
    algorithms: dict[int, list[Algorithm]] = {}
    for item in (
        Algorithm.objects.select_related("project")
        .filter(owner_id__in=ids, project__deleted_at__isnull=True)
        .order_by("project__name", "name")
    ):
        algorithms.setdefault(item.owner_id, []).append(item)
    programs: dict[int, list[LanguageProgram]] = {}
    for item in LanguageProgram.objects.filter(owner_id__in=ids).order_by("language", "name"):
        programs.setdefault(item.owner_id, []).append(item)
    exits: dict[tuple[str, object], dict[str, object]] = {}
    for log in ExerciseFocus.objects.filter(student_id__in=ids):
        summary = _focus_summary(log)
        if summary is None:
            continue
        if log.algorithm_id:
            exits[(ExerciseFeedback.ALGORITHM, log.algorithm_id)] = summary
        else:
            exits[(ExerciseFeedback.PROGRAM, log.program_id)] = summary
    marks: dict[tuple[str, object], ExerciseFeedback] = {}
    for item in ExerciseFeedback.objects.filter(teacher=teacher, student_id__in=ids):
        if item.algorithm_id:
            marks[(ExerciseFeedback.ALGORITHM, item.algorithm_id)] = item
        else:
            marks[(ExerciseFeedback.PROGRAM, item.program_id)] = item

    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, dialect="excel", lineterminator="\r\n")
    writer.writerow(
        [
            labels["name"],
            labels["email"],
            labels["communities"],
            labels["kind"],
            labels["context"],
            labels["exercise"],
            labels["grade"],
            labels["comment"],
            labels["graded_at"],
            labels["exits"],
            labels["away"],
        ]
    )
    for row in students:
        names = row["communities"]
        assert isinstance(names, list)
        person = [
            _cell(row["display_name"]),
            _cell(row["email"]),
            _cell(" | ".join(name for name in names if chosen == "" or name == chosen)),
        ]
        exercises: list[tuple[str, str, str, tuple[str, object]]] = []
        for algorithm in algorithms.get(row["id"], []):
            exercises.append(
                (
                    labels["algorithm"],
                    algorithm.project.name,
                    algorithm.name,
                    (ExerciseFeedback.ALGORITHM, algorithm.pk),
                )
            )
        for program in programs.get(row["id"], []):
            exercises.append(
                (
                    labels["program"],
                    LANGUAGE_LABELS.get(program.language, program.language),
                    program.name,
                    (ExerciseFeedback.PROGRAM, program.pk),
                )
            )
        if not exercises:
            writer.writerow([*person, "", "", "", "", "", "", "", ""])
        for kind, context, name, key in exercises:
            mark = marks.get(key)
            watched = exits.get(key)
            writer.writerow(
                [
                    *person,
                    kind,
                    _cell(context),
                    _cell(name),
                    grade_text(mark.grade) if mark else "",
                    _cell(mark.comment) if mark else "",
                    _day(mark.updated_at) if mark else "",
                    watched["exits"] if watched else "",
                    away_text(int(watched["away_seconds"])) if watched else "",
                ]
            )
    return _filename(chosen), buffer.getvalue()


def _cell(value: object) -> str:
    text = str(value)
    # Excel ejecuta una celda que empieza con estos signos como fórmula.
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text}"
    return text


def _day(value) -> str:
    return timezone.localtime(value).strftime("%Y-%m-%d")


def _filename(community: str) -> str:
    folded = unicodedata.normalize("NFKD", community).encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(char if char.isalnum() else "-" for char in folded.lower())
    cleaned = "-".join(part for part in cleaned.split("-") if part)[:60] or "alumnos"
    return f"calificaciones-{cleaned}.csv"
