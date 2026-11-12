"""Crear, asignar, resolver y calificar un examen."""

from __future__ import annotations

import csv
import io
import random
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.models import Profile, User
from apps.accounts.services import clean_label
from apps.audit.services import record
from apps.classroom.focus import (
    apply_event,
    away_text,
    close_focus,
    focus_event,
    focus_report,
    focus_start,
    watching,
)
from apps.classroom.models import Community, Membership
from apps.classroom.services import focus_rules
from apps.exams.exchange import dump_exam, parse_exam, sniff
from apps.exams.grading import as_number, grade_question, money
from apps.exams.models import Exam, ExamAttempt, ExamNotice, ExamQuestion, ExamResponse, ExamSeat
from apps.exams.payloads import clean_answer, clean_questions, clean_text
from config.errors import DomainError

NOT_FOUND = "not_found"
SUBJECTS = {
    "fundamentos": "Fundamentos",
    "bases": "Bases de datos",
    "objetos": "Programación orientada a objetos",
    "software": "Ingeniería de software",
}


def require_teacher(user: User) -> None:
    if user.profile.role != Profile.TEACHER:
        raise DomainError("Solo un docente puede crear exámenes.", status_code=403)


def require_student(user: User) -> None:
    if user.profile.role != Profile.STUDENT:
        raise DomainError("Solo un alumno puede resolver exámenes.", status_code=403)


def iso(value):
    if value is None:
        return None
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value.isoformat()


def _parse_when(value: object, field: str):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise DomainError(f"{field} no es válida.")
    parsed = parse_datetime(value)
    if parsed is None:
        raise DomainError(f"{field} no es válida.")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _flag(value: object, default: bool, message: str) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise DomainError(message)
    return value


def _as_int(value: object) -> object:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _whole(value: object, *, default: int, low: int, high: int, message: str) -> int:
    if value is None or value == "":
        return default
    value = _as_int(value)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DomainError(message)
    if value < low or value > high:
        raise DomainError(message)
    return value


def _optional_whole(value: object, message: str) -> int | None:
    if value is None or value == "":
        return None
    value = _as_int(value)
    if isinstance(value, bool) or not isinstance(value, int):
        raise DomainError(message)
    if value < 1 or value > 480:
        raise DomainError(message)
    return value


def _pass_mark(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise DomainError("La nota de aprobación no es válida.")
    try:
        number = money(Decimal(str(value)))
    except Exception as exc:
        raise DomainError("La nota de aprobación no es válida.") from exc
    if number < 0 or number > 100:
        raise DomainError("La nota de aprobación no es válida.")
    return number


def _choice(value: object, allowed: tuple[str, ...] | set[str], message: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise DomainError(message)
    return value


def _community(user: User, value: object) -> Community:
    if not isinstance(value, str) or not value:
        raise DomainError("Elige un grupo.")
    try:
        return Community.objects.get(pk=value, owner=user)
    except (Community.DoesNotExist, ValidationError, ValueError) as exc:
        raise DomainError("Ese grupo no es tuyo.") from exc


def _subject(value: object) -> str:
    if not isinstance(value, str) or value not in SUBJECTS:
        raise DomainError("La materia no es válida.")
    return value


def window_of(exam: Exam, now) -> str:
    if exam.opens_at and now < exam.opens_at:
        return "upcoming"
    if exam.closes_at and now >= exam.closes_at:
        return "closed"
    return "open"


def reveal(exam: Exam, now) -> bool:
    if exam.show_grade == Exam.IMMEDIATE:
        return True
    if exam.closes_at is None:
        return True
    return now >= exam.closes_at


def audience_users(exam: Exam) -> list[User]:
    if exam.audience == Exam.SELECTED:
        seats = exam.seats.select_related("user__profile").order_by(
            "user__profile__display_name", "user__email"
        )
        return [seat.user for seat in seats if seat.user.profile.role == Profile.STUDENT]
    memberships = exam.community.memberships.select_related("user__profile").order_by(
        "user__profile__display_name", "user__email"
    )
    return [item.user for item in memberships if item.user.profile.role == Profile.STUDENT]


def assigned(exam: Exam, user: User) -> bool:
    if exam.audience == Exam.ALL:
        return Membership.objects.filter(community=exam.community, user=user).exists()
    return ExamSeat.objects.filter(exam=exam, user=user).exists()


def get_exam(user: User, exam_id) -> Exam:
    return _owned(user, exam_id)


def _owned(user: User, exam_id) -> Exam:
    require_teacher(user)
    try:
        exam = Exam.objects.select_related("community").get(pk=exam_id, owner=user)
    except (Exam.DoesNotExist, ValidationError, ValueError) as exc:
        raise DomainError("No se encontró el examen.", code=NOT_FOUND, status_code=404) from exc
    from apps.billing.services import ensure_menu

    ensure_menu(user, "exams", exam.subject)
    return exam


def _published(exam_id) -> Exam:
    try:
        return Exam.objects.select_related("community", "owner").get(pk=exam_id, published=True)
    except (Exam.DoesNotExist, ValidationError, ValueError) as exc:
        raise DomainError("No se encontró el examen.", code=NOT_FOUND, status_code=404) from exc


def summary(exam: Exam) -> dict[str, object]:
    total = exam.questions.aggregate(total=Sum("points"))["total"] or Decimal(0)
    if exam.audience == Exam.SELECTED:
        students = exam.seats.count()
    else:
        students = exam.community.memberships.filter(user__profile__role=Profile.STUDENT).count()
    return {
        "id": str(exam.id),
        "title": exam.title,
        "subject": exam.subject,
        "community_id": str(exam.community_id),
        "community_name": exam.community.name,
        "opens_at": iso(exam.opens_at),
        "closes_at": iso(exam.closes_at),
        "duration_minutes": exam.duration_minutes,
        "published": exam.published,
        "audience": exam.audience,
        "question_count": getattr(exam, "question_count", None) or exam.questions.count(),
        "attempt_count": getattr(exam, "attempt_count", None) or exam.attempts.count(),
        "student_count": students,
        "max_points": as_number(total),
    }


def question_payload(question: ExamQuestion) -> dict[str, object]:
    return {
        "id": str(question.id),
        "kind": question.kind,
        "prompt": question.prompt,
        "points": as_number(question.points),
        "feedback": question.feedback,
        "payload": question.payload,
    }


def exam_detail(exam: Exam) -> dict[str, object]:
    questions = list(exam.questions.order_by("position"))
    total = sum((item.points for item in questions), Decimal(0))
    return {
        **summary(exam),
        "instructions": exam.instructions,
        "attempts_allowed": exam.attempts_allowed,
        "grading_method": exam.grading_method,
        "shuffle_questions": exam.shuffle_questions,
        "shuffle_choices": exam.shuffle_choices,
        "navigation": exam.navigation,
        "one_per_page": exam.one_per_page,
        "grade_to_pass": as_number(exam.grade_to_pass),
        "show_grade": exam.show_grade,
        "student_ids": list(exam.seats.values_list("user_id", flat=True)),
        "questions": [question_payload(item) for item in questions],
        "max_points": as_number(total),
        "question_count": len(questions),
    }


def list_exams(user: User, subject: object) -> list[dict[str, object]]:
    require_teacher(user)
    from apps.billing.services import menu_subjects

    query = user.exams.select_related("community").annotate(
        question_count=Count("questions", distinct=True),
        attempt_count=Count("attempts", distinct=True),
    )
    allowed = menu_subjects(user, "exams")
    if subject not in (None, ""):
        chosen = _subject(subject)
        allowed = [chosen] if chosen in allowed else []
    query = query.filter(subject__in=allowed)
    return [summary(item) for item in query]


def _students(community: Community, value: object) -> list[int]:
    if not isinstance(value, list):
        raise DomainError("Elige al menos un alumno.")
    ids: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise DomainError("Elige al menos un alumno.")
        ids.append(item)
    if not ids:
        raise DomainError("Elige al menos un alumno.")
    if len(ids) != len(set(ids)) or len(ids) > 200:
        raise DomainError("Elige al menos un alumno.")
    found = set(
        Membership.objects.filter(
            community=community,
            user_id__in=ids,
            user__profile__role=Profile.STUDENT,
        ).values_list("user_id", flat=True)
    )
    if found != set(ids):
        raise DomainError("Ese alumno no está en el grupo.")
    return ids


def _apply(exam: Exam, data: dict, user: User, *, with_questions: bool) -> None:
    if "title" in data or not exam.title:
        exam.title = clean_label(data.get("title"), field="el título", limit=140, required=True)
    if "instructions" in data or exam.pk is None:
        exam.instructions = clean_text(
            data.get("instructions", exam.instructions),
            field="las instrucciones",
            limit=4000,
            required=False,
        )
    if "community_id" in data or exam.community_id is None:
        community = _community(user, data.get("community_id"))
        subject = _subject(data.get("subject", exam.subject if exam.subject else None))
        if community.subject != subject:
            raise DomainError("Ese grupo no es de esta materia.")
        from apps.billing.services import ensure_menu, ensure_subject

        ensure_subject(user, subject)
        ensure_menu(user, "exams", subject)
        exam.community = community
        exam.subject = subject
    if "opens_at" in data or exam.pk is None:
        exam.opens_at = _parse_when(data.get("opens_at", exam.opens_at), "La apertura")
    if "closes_at" in data or exam.pk is None:
        exam.closes_at = _parse_when(data.get("closes_at", exam.closes_at), "El cierre")
    if exam.opens_at and exam.closes_at and exam.opens_at >= exam.closes_at:
        raise DomainError("La fecha de cierre es anterior a la de apertura.")
    if "duration_minutes" in data or exam.pk is None:
        exam.duration_minutes = _optional_whole(
            data.get("duration_minutes"), "El tiempo límite no es válido."
        )
    if "attempts_allowed" in data or exam.pk is None:
        exam.attempts_allowed = _whole(
            data.get("attempts_allowed", 1),
            default=1,
            low=1,
            high=20,
            message="Los intentos no son válidos.",
        )
    if "grading_method" in data or exam.pk is None:
        exam.grading_method = _choice(
            data.get("grading_method", Exam.HIGHEST),
            Exam.METHODS,
            "La forma de calificar no es válida.",
        )
    if "navigation" in data or exam.pk is None:
        exam.navigation = _choice(
            data.get("navigation", Exam.FREE),
            Exam.NAVIGATIONS,
            "La navegación no es válida.",
        )
    if "show_grade" in data or exam.pk is None:
        exam.show_grade = _choice(
            data.get("show_grade", Exam.IMMEDIATE),
            Exam.REVEALS,
            "Cuándo mostrar la nota no es válido.",
        )
    if "shuffle_questions" in data or exam.pk is None:
        exam.shuffle_questions = _flag(
            data.get("shuffle_questions"), False, "El orden de las preguntas no es válido."
        )
    if "shuffle_choices" in data or exam.pk is None:
        exam.shuffle_choices = _flag(
            data.get("shuffle_choices"), True, "El orden de las opciones no es válido."
        )
    if "one_per_page" in data or exam.pk is None:
        exam.one_per_page = _flag(
            data.get("one_per_page"), False, "La página de preguntas no es válida."
        )
    if "grade_to_pass" in data or exam.pk is None:
        exam.grade_to_pass = _pass_mark(data.get("grade_to_pass"))
    if "audience" in data or exam.pk is None:
        exam.audience = _choice(
            data.get("audience", Exam.ALL), Exam.AUDIENCES, "La audiencia no es válida."
        )
    questions = clean_questions(data.get("questions", [])) if with_questions else None
    student_ids: list[int] | None = None
    if exam.audience == Exam.SELECTED and (
        "student_ids" in data or exam.pk is None or with_questions
    ):
        student_ids = _students(exam.community, data.get("student_ids", []))
    exam.save()
    if questions is not None:
        exam.questions.all().delete()
        ExamQuestion.objects.bulk_create(
            [
                ExamQuestion(
                    exam=exam,
                    position=index,
                    kind=item["kind"],
                    prompt=item["prompt"],
                    points=item["points"],
                    feedback=item["feedback"],
                    payload=item["payload"],
                )
                for index, item in enumerate(questions, start=1)
            ]
        )
    if exam.audience == Exam.ALL:
        exam.seats.all().delete()
    elif student_ids is not None:
        exam.seats.all().delete()
        ExamSeat.objects.bulk_create([ExamSeat(exam=exam, user_id=item) for item in student_ids])


def create_exam(user: User, data: dict, ip_address: str | None) -> Exam:
    require_teacher(user)
    if user.exams.count() >= 100:
        raise DomainError("Llegaste al máximo de exámenes.")
    exam = Exam(owner=user)
    with transaction.atomic():
        _apply(exam, data, user, with_questions=True)
    record(
        "exam.create",
        actor=user,
        object_type="exam",
        object_id=str(exam.id),
        metadata={"title": exam.title, "subject": exam.subject},
        ip_address=ip_address,
    )
    return exam


def update_exam(user: User, exam_id, data: dict, ip_address: str | None) -> Exam:
    exam = _owned(user, exam_id)
    locked = exam.attempts.exists()
    structural = [
        key for key in data if key not in {"opens_at", "closes_at", "show_grade", "grade_to_pass"}
    ]
    if locked and structural:
        raise DomainError("Ya hay respuestas. Ya no se puede cambiar el examen.")
    with transaction.atomic():
        _apply(exam, data, user, with_questions=not locked and "questions" in data)
    record(
        "exam.update",
        actor=user,
        object_type="exam",
        object_id=str(exam.id),
        metadata={"title": exam.title},
        ip_address=ip_address,
    )
    return exam


def delete_exam(user: User, exam_id, ip_address: str | None) -> None:
    exam = _owned(user, exam_id)
    if exam.attempts.exists():
        raise DomainError("Ya hay respuestas. Ya no se puede eliminar el examen.")
    record(
        "exam.delete",
        actor=user,
        object_type="exam",
        object_id=str(exam.id),
        metadata={"title": exam.title},
        ip_address=ip_address,
    )
    exam.delete()


def _notify_assigned(exam: Exam) -> int:
    created = 0
    for student in audience_users(exam):
        _notice, was_created = ExamNotice.objects.get_or_create(
            exam=exam,
            user=student,
            kind=ExamNotice.ASSIGNED,
            attempt=None,
            defaults={},
        )
        if was_created:
            created += 1
    return created


def publish_exam(user: User, exam_id, ip_address: str | None) -> dict[str, object]:
    exam = _owned(user, exam_id)
    if not exam.questions.exists():
        raise DomainError("Agrega al menos una pregunta para asignar el examen.")
    if exam.audience == Exam.SELECTED and not exam.seats.exists():
        raise DomainError("Elige al menos un alumno.")
    exam.published = True
    exam.save(update_fields=["published", "updated_at"])
    notified = _notify_assigned(exam)
    record(
        "exam.publish",
        actor=user,
        object_type="exam",
        object_id=str(exam.id),
        metadata={"notified": notified},
        ip_address=ip_address,
    )
    return {**exam_detail(exam), "notified": notified}


def close_exam(user: User, exam_id, ip_address: str | None) -> Exam:
    exam = _owned(user, exam_id)
    if not exam.published:
        raise DomainError("El examen todavía no está asignado.")
    now = timezone.now()
    if exam.closes_at is None or exam.closes_at > now:
        if exam.opens_at and exam.opens_at >= now:
            exam.opens_at = now - timedelta(seconds=1)
        exam.closes_at = now
        exam.save(update_fields=["opens_at", "closes_at", "updated_at"])
    record(
        "exam.close",
        actor=user,
        object_type="exam",
        object_id=str(exam.id),
        ip_address=ip_address,
    )
    return exam


def import_exam(user: User, data: dict, ip_address: str | None) -> Exam:
    require_teacher(user)
    text = data.get("text")
    if not isinstance(text, str) or not text.strip():
        raise DomainError("El archivo está vacío.")
    if len(text) > 500_000:
        raise DomainError("El archivo es demasiado grande.")
    fmt = data.get("format") or sniff(text)
    if not isinstance(fmt, str):
        raise DomainError("No se reconoce el formato.")
    parsed = parse_exam(fmt, text)
    body = {
        "title": data.get("title") or parsed.title or "Examen importado",
        "instructions": parsed.instructions,
        "subject": data.get("subject"),
        "community_id": data.get("community_id"),
        "questions": parsed.questions,
        "audience": data.get("audience", Exam.ALL),
        "student_ids": data.get("student_ids", []),
        **parsed.settings,
    }
    exam = create_exam(user, body, ip_address)
    record(
        "exam.import",
        actor=user,
        object_type="exam",
        object_id=str(exam.id),
        metadata={"format": fmt},
        ip_address=ip_address,
    )
    return exam


def export_exam(user: User, exam_id, fmt: object) -> dict[str, str]:
    exam = _owned(user, exam_id)
    if not isinstance(fmt, str) or fmt not in {"json", "moodle", "gift"}:
        raise DomainError("No se reconoce el formato.")
    questions = [question_payload(item) for item in exam.questions.order_by("position")]
    settings = {
        "duration_minutes": exam.duration_minutes,
        "attempts_allowed": exam.attempts_allowed,
        "grading_method": exam.grading_method,
        "shuffle_questions": exam.shuffle_questions,
        "shuffle_choices": exam.shuffle_choices,
        "navigation": exam.navigation,
        "one_per_page": exam.one_per_page,
        "grade_to_pass": as_number(exam.grade_to_pass),
        "show_grade": exam.show_grade,
    }
    filename, content, media = dump_exam(fmt, exam.title, exam.instructions, settings, questions)
    return {"filename": filename, "content": content, "media_type": media}


def _person(user: User) -> dict[str, object]:
    return {"id": user.pk, "display_name": user.profile.display_name, "email": user.email}


def _official(exam: Exam, attempts: list[ExamAttempt]) -> dict[str, object]:
    graded = [
        item for item in attempts if item.state == ExamAttempt.GRADED and item.percent is not None
    ]
    pending = any(item.state == ExamAttempt.SUBMITTED for item in attempts)
    if not graded:
        return {
            "percent": None,
            "score": None,
            "max_score": None,
            "passed": None,
            "pending": pending,
            "attempt_id": None,
        }
    if exam.grading_method == Exam.AVERAGE:
        percent = money(sum((item.percent for item in graded), Decimal(0)) / Decimal(len(graded)))
        score = money(
            sum((item.score or Decimal(0) for item in graded), Decimal(0)) / Decimal(len(graded))
        )
        chosen = graded[-1]
        passed = None if exam.grade_to_pass is None else percent >= exam.grade_to_pass
        return {
            "percent": as_number(percent),
            "score": as_number(score),
            "max_score": as_number(chosen.max_score),
            "passed": passed,
            "pending": pending,
            "attempt_id": str(chosen.id),
        }
    if exam.grading_method == Exam.FIRST:
        chosen = graded[0]
    elif exam.grading_method == Exam.LAST:
        chosen = graded[-1]
    else:
        chosen = max(graded, key=lambda item: (item.percent, -item.number))
    return {
        "percent": as_number(chosen.percent),
        "score": as_number(chosen.score),
        "max_score": as_number(chosen.max_score),
        "passed": chosen.passed,
        "pending": pending,
        "attempt_id": str(chosen.id),
    }


def _expire(attempt: ExamAttempt, now) -> ExamAttempt:
    if attempt.state != ExamAttempt.OPEN or attempt.deadline is None or now <= attempt.deadline:
        return attempt
    with transaction.atomic():
        locked = ExamAttempt.objects.select_for_update().select_related("exam").get(pk=attempt.pk)
        if locked.state != ExamAttempt.OPEN or locked.deadline is None or now <= locked.deadline:
            return locked
        return _grade_open(locked, None)


def list_mine(user: User) -> list[dict[str, object]]:
    require_student(user)
    communities = Membership.objects.filter(user=user).values_list("community_id", flat=True)
    seat_ids = ExamSeat.objects.filter(user=user).values_list("exam_id", flat=True)
    attempt_ids = ExamAttempt.objects.filter(student=user).values_list("exam_id", flat=True)
    from apps.billing.services import menu_subjects

    exams = (
        Exam.objects.filter(published=True, subject__in=menu_subjects(user, "exams"))
        .filter(
            Q(audience=Exam.ALL, community_id__in=communities)
            | Q(pk__in=seat_ids)
            | Q(pk__in=attempt_ids)
        )
        .select_related("community")
        .distinct()
        .order_by("opens_at", "title")
    )
    now = timezone.now()
    cards = []
    for exam in exams:
        attempts = list(exam.attempts.filter(student=user).order_by("number"))
        attempts = [
            _expire(item, now) if item.state == ExamAttempt.OPEN else item for item in attempts
        ]
        open_attempt = next((item for item in attempts if item.state == ExamAttempt.OPEN), None)
        finished = [item for item in attempts if item.state != ExamAttempt.OPEN]
        state = window_of(exam, now)
        cards.append(
            {
                "id": str(exam.id),
                "title": exam.title,
                "instructions": exam.instructions,
                "subject": exam.subject,
                "community_name": exam.community.name,
                "opens_at": iso(exam.opens_at),
                "closes_at": iso(exam.closes_at),
                "duration_minutes": exam.duration_minutes,
                "attempts_allowed": exam.attempts_allowed,
                "attempts_used": len(attempts),
                "window": state,
                "can_start": state == "open"
                and open_attempt is None
                and len(attempts) < exam.attempts_allowed,
                "open_attempt_id": str(open_attempt.id) if open_attempt else None,
                "latest_attempt_id": str(finished[-1].id) if finished else None,
                "navigation": exam.navigation,
                "one_per_page": exam.one_per_page,
                "show_grade": exam.show_grade,
                "official": _official(exam, attempts),
            }
        )
    return cards


def list_notices(user: User) -> dict[str, object]:
    if user.profile.role not in {Profile.STUDENT, Profile.TEACHER}:
        raise DomainError("Solo un alumno o un docente puede ver los avisos.", status_code=403)
    from apps.billing.services import menu_subjects

    now = timezone.now()
    allowed = set(menu_subjects(user, "exams"))
    notices = ExamNotice.objects.filter(user=user).select_related("exam", "exam__community")
    results = []
    unread = 0
    for notice in notices:
        if notice.exam.subject not in allowed:
            continue
        if notice.read_at is None:
            unread += 1
        visible = (
            notice.percent
            if notice.kind == ExamNotice.GRADED and reveal(notice.exam, now)
            else None
        )
        results.append(
            {
                "id": str(notice.id),
                "exam_id": str(notice.exam_id),
                "kind": notice.kind,
                "title": notice.exam.title,
                "subject": notice.exam.subject,
                "group": notice.exam.community.name,
                "opens_at": iso(notice.exam.opens_at),
                "closes_at": iso(notice.exam.closes_at),
                "duration_minutes": notice.exam.duration_minutes,
                "percent": as_number(visible) if visible is not None else None,
                "created_at": iso(notice.created_at),
                "read": notice.read_at is not None,
            }
        )
    return {"unread": unread, "results": results}


def mark_notices(user: User) -> dict[str, object]:
    ExamNotice.objects.filter(user=user, read_at__isnull=True).update(read_at=timezone.now())
    return list_notices(user)


def _layout(exam: Exam, questions: list[ExamQuestion]) -> dict[str, object]:
    rng = random.SystemRandom()
    order = [str(item.id) for item in questions]
    if exam.shuffle_questions:
        rng.shuffle(order)
    bundles: dict[str, list[str]] = {}
    for question in questions:
        payload = question.payload
        if question.kind in {ExamQuestion.CHOICE, ExamQuestion.MULTI} and exam.shuffle_choices:
            ids = [item["id"] for item in payload.get("options", [])]
            rng.shuffle(ids)
            bundles[str(question.id)] = ids
        elif question.kind == ExamQuestion.ORDER:
            ids = [item["id"] for item in payload.get("items", [])]
            rng.shuffle(ids)
            bundles[str(question.id)] = ids
        elif question.kind == ExamQuestion.MATCHING:
            ids = [item["id"] for item in payload.get("pairs", [])]
            rng.shuffle(ids)
            bundles[str(question.id)] = ids
    return {"order": order, "bundles": bundles}


def _deadline(exam: Exam, started):
    moments = []
    if exam.duration_minutes:
        moments.append(started + timedelta(minutes=exam.duration_minutes))
    if exam.closes_at:
        moments.append(exam.closes_at)
    return min(moments) if moments else None


def start_attempt(user: User, exam_id, ip_address: str | None) -> ExamAttempt:
    require_student(user)
    exam = _published(exam_id)
    from apps.billing.services import ensure_menu

    ensure_menu(user, "exams", exam.subject)
    if not assigned(exam, user):
        raise DomainError("No tienes este examen.", status_code=403)
    now = timezone.now()
    try:
        with transaction.atomic():
            exam = Exam.objects.select_for_update().get(pk=exam.pk)
            current = (
                ExamAttempt.objects.filter(exam=exam, student=user, state=ExamAttempt.OPEN)
                .order_by("number")
                .first()
            )
            if current is not None:
                current = _expire(current, now)
                if current.state == ExamAttempt.OPEN:
                    return current
            state = window_of(exam, now)
            if state == "upcoming":
                raise DomainError("El examen todavía no abre.")
            if state == "closed":
                raise DomainError("El examen ya cerró.")
            used = ExamAttempt.objects.filter(exam=exam, student=user).count()
            if used >= exam.attempts_allowed:
                raise DomainError("Ya usaste los intentos de este examen.")
            questions = list(exam.questions.order_by("position"))
            started = timezone.now()
            attempt = ExamAttempt.objects.create(
                exam=exam,
                student=user,
                number=used + 1,
                deadline=_deadline(exam, started),
                layout=_layout(exam, questions),
                max_score=sum((item.points for item in questions), Decimal(0)),
                focus=focus_start(focus_rules(user, exam.community)),
            )
    except IntegrityError as exc:
        current = ExamAttempt.objects.filter(
            exam_id=exam_id, student=user, state=ExamAttempt.OPEN
        ).first()
        if current is not None:
            return current
        raise DomainError("Ya usaste los intentos de este examen.") from exc
    record(
        "exam.start",
        actor=user,
        object_type="exam_attempt",
        object_id=str(attempt.id),
        metadata={"exam": str(exam.id)},
        ip_address=ip_address,
    )
    return attempt


def _student_attempt(user: User, attempt_id) -> ExamAttempt:
    require_student(user)
    try:
        attempt = ExamAttempt.objects.select_related("exam", "exam__community").get(
            pk=attempt_id, student=user
        )
    except (ExamAttempt.DoesNotExist, ValidationError, ValueError) as exc:
        raise DomainError("No se encontró el intento.", code=NOT_FOUND, status_code=404) from exc
    from apps.billing.services import ensure_menu

    ensure_menu(user, "exams", attempt.exam.subject)
    return attempt


def _owned_attempt(user: User, attempt_id) -> ExamAttempt:
    require_teacher(user)
    try:
        attempt = ExamAttempt.objects.select_related("exam", "student__profile").get(
            pk=attempt_id, exam__owner=user
        )
    except (ExamAttempt.DoesNotExist, ValidationError, ValueError) as exc:
        raise DomainError("No se encontró el intento.", code=NOT_FOUND, status_code=404) from exc
    from apps.billing.services import ensure_menu

    ensure_menu(user, "exams", attempt.exam.subject)
    return attempt


def _answers(attempt: ExamAttempt, value: object) -> dict[str, dict]:
    stored = {str(item.question_id): item.answer for item in attempt.responses.all()}
    if value is None:
        return stored
    if not isinstance(value, list):
        raise DomainError("Las respuestas no son válidas.")
    valid = {str(item.id) for item in attempt.exam.questions.all()}
    merged = dict(stored)
    for item in value:
        if not isinstance(item, dict):
            raise DomainError("Las respuestas no son válidas.")
        question_id = item.get("question_id")
        if not isinstance(question_id, str) or question_id not in valid:
            raise DomainError("La pregunta no es de este examen.")
        merged[question_id] = clean_answer(item.get("answer"))
    return merged


def _write_answers(attempt: ExamAttempt, answers: dict[str, dict], *, grade: bool) -> None:
    questions = list(attempt.exam.questions.order_by("position"))
    for question in questions:
        answer = answers.get(str(question.id), {})
        if not isinstance(answer, dict):
            answer = {}
        if grade:
            mark = grade_question(question.kind, question.payload, answer, question.points)
            defaults = {
                "answer": answer,
                "score": None if mark.pending else mark.score,
                "max_score": question.points,
                "pending": mark.pending,
                "comment": "",
                "detail": mark.detail,
            }
        else:
            defaults = {"answer": answer, "max_score": question.points}
        ExamResponse.objects.update_or_create(attempt=attempt, question=question, defaults=defaults)


def _recompute(attempt: ExamAttempt) -> None:
    exam = attempt.exam
    responses = list(attempt.responses.all())
    pending = any(item.pending for item in responses)
    total = sum((item.score or Decimal(0) for item in responses), Decimal(0))
    max_score = sum((item.points for item in exam.questions.all()), Decimal(0))
    percent = Decimal(0) if max_score == 0 else money(total * Decimal(100) / max_score)
    attempt.score = money(total)
    attempt.max_score = money(max_score)
    attempt.percent = percent
    if pending or exam.grade_to_pass is None:
        attempt.passed = None
    else:
        attempt.passed = percent >= exam.grade_to_pass
    attempt.state = ExamAttempt.SUBMITTED if pending else ExamAttempt.GRADED
    if attempt.submitted_at is None:
        attempt.submitted_at = timezone.now()
    attempt.save()


def _notify_graded(attempt: ExamAttempt) -> None:
    ExamNotice.objects.get_or_create(
        attempt=attempt,
        kind=ExamNotice.GRADED,
        defaults={"exam": attempt.exam, "user": attempt.student, "percent": attempt.percent},
    )


def _grade_open(attempt: ExamAttempt, raw_answers: object) -> ExamAttempt:
    if attempt.state != ExamAttempt.OPEN:
        return attempt
    answers = _answers(attempt, raw_answers)
    _write_answers(attempt, answers, grade=True)
    _recompute(attempt)
    if attempt.state == ExamAttempt.GRADED:
        _notify_graded(attempt)
    return attempt


def save_attempt(user: User, attempt_id, data: dict, ip_address: str | None) -> ExamAttempt:
    attempt = _student_attempt(user, attempt_id)
    with transaction.atomic():
        attempt = ExamAttempt.objects.select_for_update().select_related("exam").get(pk=attempt.pk)
        if attempt.state != ExamAttempt.OPEN:
            raise DomainError("Este intento ya se entregó.")
        now = timezone.now()
        if attempt.deadline is not None and now > attempt.deadline:
            return _grade_open(attempt, data.get("answers"))
        _write_answers(attempt, _answers(attempt, data.get("answers")), grade=False)
    record(
        "exam.save",
        actor=user,
        object_type="exam_attempt",
        object_id=str(attempt.id),
        ip_address=ip_address,
    )
    return attempt


def submit_attempt(user: User, attempt_id, data: dict, ip_address: str | None) -> ExamAttempt:
    attempt = _student_attempt(user, attempt_id)
    with transaction.atomic():
        attempt = ExamAttempt.objects.select_for_update().select_related("exam").get(pk=attempt.pk)
        if attempt.state == ExamAttempt.OPEN:
            attempt = _grade_open(attempt, data.get("answers"))
            record(
                "exam.submit",
                actor=user,
                object_type="exam_attempt",
                object_id=str(attempt.id),
                metadata={"percent": as_number(attempt.percent)},
                ip_address=ip_address,
            )
    return attempt


def focus_attempt(user: User, attempt_id, data: dict, ip_address: str | None) -> ExamAttempt:
    """Registra una salida o un regreso. Al llegar al límite del grupo entrega lo que haya."""
    event, reason = focus_event(data)
    attempt = _student_attempt(user, attempt_id)
    with transaction.atomic():
        attempt = ExamAttempt.objects.select_for_update().select_related("exam").get(pk=attempt.pk)
        if attempt.state != ExamAttempt.OPEN or not watching(attempt.focus):
            return attempt
        now = timezone.now()
        if attempt.deadline is not None and now > attempt.deadline:
            return _grade_open(attempt, None)
        attempt.focus, reached = apply_event(attempt.focus, event, reason, now)
        if not reached:
            attempt.save(update_fields=["focus"])
            return attempt
        attempt.focus = close_focus(attempt.focus, now)
        try:
            answers = _answers(attempt, data.get("answers"))
        except DomainError:
            answers = _answers(attempt, None)
        _write_answers(attempt, answers, grade=True)
        _recompute(attempt)
        if attempt.state == ExamAttempt.GRADED:
            _notify_graded(attempt)
    record(
        "exam.focus_submit",
        actor=user,
        object_type="exam_attempt",
        object_id=str(attempt.id),
        metadata={"exits": attempt.focus.get("exits")},
        ip_address=ip_address,
    )
    return attempt


def grade_manual(user: User, attempt_id, data: dict, ip_address: str | None) -> ExamAttempt:
    attempt = _owned_attempt(user, attempt_id)
    if attempt.state == ExamAttempt.OPEN:
        raise DomainError("El alumno todavía no entrega.")
    scores = data.get("scores")
    if not isinstance(scores, list) or not scores:
        raise DomainError("Indica la calificación.")
    with transaction.atomic():
        attempt = ExamAttempt.objects.select_for_update().select_related("exam").get(pk=attempt.pk)
        was_graded = attempt.state == ExamAttempt.GRADED
        for item in scores:
            if not isinstance(item, dict):
                raise DomainError("Indica la calificación.")
            question_id = item.get("question_id")
            try:
                response = ExamResponse.objects.get(attempt=attempt, question_id=question_id)
            except (ExamResponse.DoesNotExist, ValidationError, ValueError) as exc:
                raise DomainError("La pregunta no es de este examen.") from exc
            number = _pass_mark(item.get("score"))
            if number is None or number > response.max_score:
                raise DomainError("El puntaje no es válido.")
            response.score = number
            response.pending = False
            if "comment" in item:
                response.comment = clean_text(
                    item.get("comment"), field="el comentario", limit=1000, required=False
                )
            response.save(update_fields=["score", "pending", "comment"])
        _recompute(attempt)
        if not was_graded and attempt.state == ExamAttempt.GRADED:
            _notify_graded(attempt)
    record(
        "exam.grade",
        actor=user,
        object_type="exam_attempt",
        object_id=str(attempt.id),
        ip_address=ip_address,
    )
    return attempt


def _ordered_questions(attempt: ExamAttempt) -> list[ExamQuestion]:
    questions = {str(item.id): item for item in attempt.exam.questions.all()}
    order = attempt.layout.get("order") if isinstance(attempt.layout, dict) else None
    if not isinstance(order, list):
        return sorted(questions.values(), key=lambda item: item.position)
    ordered = [questions[item] for item in order if isinstance(item, str) and item in questions]
    seen = {str(item.id) for item in ordered}
    for question in sorted(questions.values(), key=lambda item: item.position):
        if str(question.id) not in seen:
            ordered.append(question)
    return ordered


def _show_payload(question: ExamQuestion, layout: dict, *, secrets: bool) -> dict:
    payload = question.payload if isinstance(question.payload, dict) else {}
    bundles = layout.get("bundles") if isinstance(layout, dict) else {}
    bundle = bundles.get(str(question.id)) if isinstance(bundles, dict) else None
    if question.kind in {ExamQuestion.CHOICE, ExamQuestion.MULTI}:
        options = list(payload.get("options") or [])
        if isinstance(bundle, list):
            rank = {ident: index for index, ident in enumerate(bundle) if isinstance(ident, str)}
            options = sorted(options, key=lambda item: rank.get(item.get("id"), 0))
        if secrets:
            return {"options": options}
        return {
            "options": [
                {"id": item["id"], "text": item["text"]}
                for item in options
                if isinstance(item, dict)
            ]
        }
    if question.kind == ExamQuestion.ORDER:
        items = list(payload.get("items") or [])
        if secrets:
            return payload
        if isinstance(bundle, list):
            rank = {ident: index for index, ident in enumerate(bundle) if isinstance(ident, str)}
            items = sorted(items, key=lambda item: rank.get(item.get("id"), 0))
        return {
            "items": [
                {"id": item["id"], "text": item["text"]} for item in items if isinstance(item, dict)
            ]
        }
    if question.kind == ExamQuestion.MATCHING:
        pairs = [item for item in payload.get("pairs") or [] if isinstance(item, dict)]
        if secrets:
            return payload
        rights = list(pairs)
        if isinstance(bundle, list):
            rank = {ident: index for index, ident in enumerate(bundle) if isinstance(ident, str)}
            rights = sorted(rights, key=lambda item: rank.get(item.get("id"), 0))
        return {
            "left": [{"id": item["id"], "text": item["left"]} for item in pairs],
            "right": [{"id": item["id"], "text": item["right"]} for item in rights],
        }
    if question.kind == ExamQuestion.CLOZE:
        if secrets:
            return payload
        return {
            "text": payload.get("text", ""),
            "blanks": [
                {"id": item["id"]} for item in payload.get("blanks") or [] if isinstance(item, dict)
            ],
        }
    if question.kind == ExamQuestion.CASE:
        cases = [item for item in payload.get("cases") or [] if isinstance(item, dict)]
        if secrets:
            return payload
        visible = []
        hidden = 0
        for case in cases:
            if case.get("hidden") is True:
                hidden += 1
                continue
            visible.append({"name": case.get("name", ""), "inputs": case.get("inputs") or []})
        return {
            "statement": payload.get("statement", ""),
            "starter": payload.get("starter", ""),
            "cases": visible,
            "hidden_count": hidden,
        }
    if question.kind == ExamQuestion.SHORT:
        if secrets:
            return payload
        return {"case_sensitive": payload.get("case_sensitive") is True}
    if question.kind == ExamQuestion.NUMERICAL:
        return payload if secrets else {}
    if question.kind == ExamQuestion.TRUE_FALSE:
        return payload if secrets else {}
    if question.kind == ExamQuestion.ESSAY:
        return {"rubric": payload.get("rubric", "")}
    return {}


def _public_detail(kind: str, detail: object, *, secrets: bool) -> dict:
    if not isinstance(detail, dict):
        return {}
    if kind != ExamQuestion.CASE or secrets:
        return detail
    rows = []
    for row in detail.get("cases") or []:
        if not isinstance(row, dict):
            continue
        if row.get("hidden") is True:
            rows.append({"name": row.get("name", ""), "ok": row.get("ok"), "hidden": True})
        else:
            rows.append(row)
    return {"cases": rows}


def attempt_view(attempt: ExamAttempt, *, teacher: bool) -> dict[str, object]:
    exam = attempt.exam
    now = timezone.now()
    secrets = teacher or (attempt.state != ExamAttempt.OPEN and reveal(exam, now))
    responses = {str(item.question_id): item for item in attempt.responses.all()}
    questions = []
    for question in _ordered_questions(attempt):
        response = responses.get(str(question.id))
        row: dict[str, object] = {
            "id": str(question.id),
            "kind": question.kind,
            "prompt": question.prompt,
            "points": as_number(question.points),
            "payload": _show_payload(
                question,
                attempt.layout if isinstance(attempt.layout, dict) else {},
                secrets=secrets,
            ),
            "answer": response.answer if response else {},
        }
        if secrets:
            row["feedback"] = question.feedback
        if response is not None and (teacher or attempt.state != ExamAttempt.OPEN):
            if secrets:
                row["score"] = as_number(response.score)
                row["comment"] = response.comment
                row["detail"] = _public_detail(question.kind, response.detail, secrets=teacher)
            row["pending"] = response.pending
        questions.append(row)
    body: dict[str, object] = {
        "id": str(attempt.id),
        "exam_id": str(exam.id),
        "number": attempt.number,
        "state": attempt.state,
        "started_at": iso(attempt.started_at),
        "deadline": iso(attempt.deadline),
        "submitted_at": iso(attempt.submitted_at),
        "title": exam.title,
        "instructions": exam.instructions,
        "subject": exam.subject,
        "navigation": exam.navigation,
        "one_per_page": exam.one_per_page,
        "graded_visible": secrets and attempt.state != ExamAttempt.OPEN,
        "pending": attempt.state == ExamAttempt.SUBMITTED,
        "questions": questions,
        "focus": focus_report(
            attempt.focus, now if attempt.state == ExamAttempt.OPEN else attempt.submitted_at
        ),
    }
    if secrets and attempt.state != ExamAttempt.OPEN:
        body["score"] = as_number(attempt.score)
        body["max_score"] = as_number(attempt.max_score)
        body["percent"] = as_number(attempt.percent)
        body["passed"] = attempt.passed
    return body


def open_attempt(user: User, attempt_id) -> dict[str, object]:
    attempt = _student_attempt(user, attempt_id)
    now = timezone.now()
    if attempt.state == ExamAttempt.OPEN:
        attempt = _expire(attempt, now)
    return attempt_view(attempt, teacher=False)


def results(user: User, exam_id) -> dict[str, object]:
    exam = _owned(user, exam_id)
    questions = [question_payload(item) for item in exam.questions.order_by("position")]
    people = {student.pk: student for student in audience_users(exam)}
    for attempt in exam.attempts.select_related("student__profile"):
        people.setdefault(attempt.student_id, attempt.student)
    rows = []
    for student in people.values():
        attempts = list(exam.attempts.filter(student=student).order_by("number"))
        rendered = []
        for attempt in attempts:
            view = attempt_view(attempt, teacher=True)
            rendered.append(
                {
                    "id": view["id"],
                    "number": view["number"],
                    "state": view["state"],
                    "started_at": view["started_at"],
                    "submitted_at": view["submitted_at"],
                    "score": view.get("score"),
                    "max_score": view.get("max_score"),
                    "percent": view.get("percent"),
                    "passed": view.get("passed"),
                    "pending": view["pending"],
                    "questions": view["questions"],
                    "focus": view["focus"],
                }
            )
        rows.append(
            {
                "student": _person(student),
                "official": _official(exam, attempts),
                "attempts": rendered,
            }
        )
    return {"exam": exam_detail(exam), "questions": questions, "rows": rows}


def _answer_text(question: ExamQuestion, answer: object) -> str:
    if not isinstance(answer, dict):
        return ""
    payload = question.payload if isinstance(question.payload, dict) else {}
    if question.kind == ExamQuestion.CHOICE:
        labels = {
            item["id"]: item["text"]
            for item in payload.get("options") or []
            if isinstance(item, dict)
        }
        text = labels.get(answer.get("option"), "")
    elif question.kind == ExamQuestion.MULTI:
        labels = {
            item["id"]: item["text"]
            for item in payload.get("options") or []
            if isinstance(item, dict)
        }
        picked = answer.get("options") if isinstance(answer.get("options"), list) else []
        text = " | ".join(str(labels.get(item, item)) for item in picked)
    elif question.kind == ExamQuestion.TRUE_FALSE:
        value = answer.get("value")
        text = "Verdadero" if value is True else "Falso" if value is False else ""
    elif question.kind in {ExamQuestion.SHORT, ExamQuestion.ESSAY}:
        text = answer.get("text") if isinstance(answer.get("text"), str) else ""
    elif question.kind == ExamQuestion.NUMERICAL:
        text = "" if answer.get("value") is None else str(answer.get("value"))
    elif question.kind == ExamQuestion.MATCHING:
        pairs = answer.get("pairs") if isinstance(answer.get("pairs"), dict) else {}
        text = ", ".join(f"{key}->{value}" for key, value in pairs.items())
    elif question.kind == ExamQuestion.ORDER:
        order = answer.get("order") if isinstance(answer.get("order"), list) else []
        labels = {
            item["id"]: item["text"]
            for item in payload.get("items") or []
            if isinstance(item, dict)
        }
        text = " | ".join(str(labels.get(item, item)) for item in order)
    elif question.kind == ExamQuestion.CLOZE:
        blanks = answer.get("blanks") if isinstance(answer.get("blanks"), dict) else {}
        text = ", ".join(f"{key}={value}" for key, value in blanks.items())
    else:
        text = answer.get("source") if isinstance(answer.get("source"), str) else ""
    return " ".join(str(text).split())[:500]


def _focus_cells(attempt: ExamAttempt) -> list[object]:
    report = focus_report(attempt.focus, attempt.submitted_at or timezone.now())
    if report is None:
        return ["", ""]
    return [report["exits"], away_text(int(report["away_seconds"]))]


def grades_csv(user: User, exam_id) -> dict[str, str]:
    exam = _owned(user, exam_id)
    questions = list(exam.questions.order_by("position"))
    people = {student.pk: student for student in audience_users(exam)}
    for attempt in exam.attempts.select_related("student__profile"):
        people.setdefault(attempt.student_id, attempt.student)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    header = [
        "Alumno",
        "Correo",
        "Grupo",
        "Materia",
        "Examen",
        "Intento",
        "Inicio",
        "Entrega",
        "Estado",
        "Puntaje",
        "Maximo",
        "Porcentaje",
        "Aprobado",
        "Salidas",
        "Tiempo fuera",
    ]
    for index, _question in enumerate(questions, start=1):
        header.extend([f"P{index} puntaje", f"P{index} respuesta"])
    writer.writerow(header)
    subject = SUBJECTS.get(exam.subject, exam.subject)
    for student in people.values():
        attempts = list(exam.attempts.filter(student=student).order_by("number"))
        if not attempts:
            writer.writerow(
                [
                    student.profile.display_name,
                    student.email,
                    exam.community.name,
                    subject,
                    exam.title,
                    "",
                    "",
                    "",
                    "sin iniciar",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
            continue
        for attempt in attempts:
            responses = {str(item.question_id): item for item in attempt.responses.all()}
            passed = "" if attempt.passed is None else "sí" if attempt.passed else "no"
            row = [
                student.profile.display_name,
                student.email,
                exam.community.name,
                subject,
                exam.title,
                attempt.number,
                iso(attempt.started_at),
                iso(attempt.submitted_at) or "",
                attempt.state,
                "" if attempt.score is None else as_number(attempt.score),
                as_number(attempt.max_score),
                "" if attempt.percent is None else as_number(attempt.percent),
                passed,
                *_focus_cells(attempt),
            ]
            for question in questions:
                response = responses.get(str(question.id))
                row.append(
                    "" if response is None or response.score is None else as_number(response.score)
                )
                row.append("" if response is None else _answer_text(question, response.answer))
            writer.writerow(row)
    filename = f"{exam.title}.csv"
    return {"filename": filename, "content": "\ufeff" + buffer.getvalue(), "media_type": "text/csv"}
