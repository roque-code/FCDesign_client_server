"""Intentos, pistas y predicción. No escribe proyectos ni ejecuciones del editor."""

from __future__ import annotations

import math
import random
import time
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import Profile
from apps.accounts.services import standing_of
from apps.classroom.models import Membership
from apps.language.services import diagnostic_payload
from apps.learning.models import (
    Challenge,
    ChallengeAttempt,
    ConceptMastery,
    HintUsage,
    LearningPath,
    PathAssignment,
    PathEntry,
    Prediction,
    Reflection,
    WorkspaceSnapshot,
)
from apps.learning.services import load_workspace
from config.errors import DomainError
from language_core.ast_nodes import dump
from language_core.block_adapter import adapt_workspace
from language_core.debugger import drive
from language_core.grammar import STRICT
from language_core.interpreter import Interpreter
from language_core.runtime import Cancellation, Limits

_WEIGHTS = {
    "comprension": 20,
    "diseno": 25,
    "correccion": 30,
    "explicacion": 15,
    "autonomia": 10,
}
_SOLUTION_MARK = "Esta es la solución explicada"


def path_payload(user, path: LearningPath | None = None) -> dict[str, object]:
    chosen = path or _path()
    if path is not None and not can_see_path(user, chosen):
        raise DomainError("No se encontró la ruta.", code="not_found", status_code=404)
    challenges = _sequence(chosen, user)
    completed = set(
        ChallengeAttempt.objects.filter(
            user=user, status=ChallengeAttempt.COMPLETED, challenge__in=challenges
        ).values_list("challenge_id", flat=True)
    )
    closed_counts = {
        row["challenge_id"]: row["total"]
        for row in ChallengeAttempt.objects.filter(
            user=user,
            challenge__in=challenges,
            status__in=[ChallengeAttempt.COMPLETED, ChallengeAttempt.ABANDONED],
        )
        .values("challenge_id")
        .annotate(total=Count("id"))
    }
    windows = _windows(chosen)
    withdrawn_ids = _withdrawn_ids(chosen)
    now = timezone.now()
    rows: list[dict[str, object]] = []
    previous_linked_done = True
    for index, challenge in enumerate(challenges, start=1):
        opens_at, closes_at = windows.get(challenge.id, (None, None))
        scheduled = opens_at is not None or closes_at is not None
        if challenge.id in completed:
            state = "completed"
        elif scheduled and opens_at is not None and now < opens_at:
            state = "scheduled"
        elif scheduled and closes_at is not None and now >= closes_at:
            state = "closed"
        elif scheduled or previous_linked_done:
            state = "available"
        else:
            state = "locked"
        if not scheduled:
            previous_linked_done = challenge.id in completed
        rows.append(
            {
                "id": str(challenge.id),
                "title": challenge.title,
                "activity_type": challenge.activity_type,
                "difficulty": challenge.difficulty,
                "points": challenge.points,
                "concept": challenge.unit.concept.name,
                "position": index,
                "state": state,
                "opens_at": _iso(opens_at),
                "closes_at": _iso(closes_at),
                "withdrawn": challenge.id in withdrawn_ids,
                "time_limit_seconds": challenge.time_limit_seconds,
                "attempt_count": closed_counts.get(challenge.id, 0),
            }
        )
    return {
        "id": str(chosen.id),
        "name": chosen.name,
        "description": chosen.description,
        "challenges": rows,
    }


def paths_payload(user) -> dict[str, object]:
    return {"results": [path_payload(user, path) for path in visible_paths(user)]}


def can_see_path(user, path: LearningPath) -> bool:
    if path.owner_id == user.pk:
        return True
    if not path.is_published:
        return False
    if path.owner_id is None:
        return True
    if PathAssignment.objects.filter(path=path, student=user).exists():
        return True
    return PathAssignment.objects.filter(
        path=path,
        community__memberships__user=user,
    ).exists()


def visible_paths(user) -> list[LearningPath]:
    communities = Membership.objects.filter(user=user).values("community_id")
    query = Q(owner__isnull=True, is_published=True) | Q(owner=user)
    query |= Q(is_published=True, assignments__student=user)
    query |= Q(is_published=True, assignments__community_id__in=communities)
    return list(
        LearningPath.objects.filter(query)
        .exclude(is_bank=True)
        .distinct()
        .order_by("position", "name")
    )


def challenge_payload(user, challenge_id) -> dict[str, object]:
    challenge = _published(challenge_id)
    _ensure_unlocked(user, challenge)
    attempt = (
        ChallengeAttempt.objects.filter(user=user, challenge=challenge)
        .order_by("-started_at")
        .first()
    )
    return {
        "challenge": _public_challenge(challenge),
        "attempt": _state(attempt) if attempt else None,
    }


def start_attempt(user, challenge_id, path_id: object = None) -> dict[str, object]:
    challenge = _published(challenge_id)
    path = _bound_path(user, challenge, path_id)
    _ensure_unlocked(user, challenge, path)
    _ensure_open(user, challenge, path)
    with transaction.atomic():
        get_user_model().objects.select_for_update().get(pk=user.pk)
        current = _existing_attempt(user, challenge)
        if current is not None and current.status == ChallengeAttempt.OPEN and _late(current):
            _abandon(current)
            current = None
        if current is None:
            current = ChallengeAttempt.objects.create(user=user, challenge=challenge)
    return _bundle(current)


def save_stage(user, attempt_id, stage: object, answer: object) -> dict[str, object]:
    attempt = _open_attempt(user, attempt_id)
    if stage not in ("comprender", "razonar"):
        raise DomainError("La etapa no es válida.")
    expected = _next(attempt)
    if stage != expected and not (stage == "razonar" and expected == "razonar"):
        if stage == "comprender" and _has(attempt, "comprender"):
            return _bundle(attempt)
        raise DomainError("Esa etapa todavía no está abierta.", code="conflict", status_code=409)
    if stage == "comprender":
        if not isinstance(answer, dict) or answer.get("ack") is not True:
            raise DomainError("Confirma que comprendiste el enunciado.")
        _remember(attempt, "comprender", answer)
        return _bundle(attempt)
    correct = _grade_answer(attempt.challenge, answer)
    _remember(attempt, "razonar", answer if isinstance(answer, dict) else {"text": answer})
    if attempt.challenge.activity_type == "predict" and isinstance(answer, dict):
        text = answer.get("text")
        if isinstance(text, str):
            _store_prediction(attempt, text, correct)
    return _bundle(attempt, correct=correct)


def reveal_hint(user, attempt_id) -> dict[str, object]:
    attempt = _open_attempt(user, attempt_id)
    used = set(attempt.hint_usages.values_list("hint_id", flat=True))
    hints = list(attempt.challenge.hints.order_by("level", "position"))
    nxt = next((hint for hint in hints if hint.id not in used), None)
    if nxt is None:
        raise DomainError("Ya no quedan pistas.", code="conflict", status_code=409)
    HintUsage.objects.create(attempt=attempt, hint=nxt)
    return _bundle(attempt)


def check_attempt(user, attempt_id, data: dict[str, Any]) -> dict[str, object]:
    attempt = _open_attempt(user, attempt_id)
    if attempt.challenge.activity_type != Challenge.BUILD:
        raise DomainError("Este reto no se comprueba con el lienzo.")
    if _next(attempt) not in ("construir", "comprobar"):
        raise DomainError(
            "Termina el análisis antes de comprobar.", code="conflict", status_code=409
        )
    workspace = load_workspace(data)
    concept = attempt.challenge.unit.concept.name
    foreign = _foreign_blocks(workspace, list(attempt.challenge.allowed_blocks))
    if foreign:
        _remember(attempt, "comprobar", {"passed": False})
        return _bundle(
            attempt,
            passed=False,
            diagnostics=[
                {
                    "severity": "error",
                    "code": "L0102",
                    "message": f"{concept}: Este reto no usa ese bloque.",
                    "line": 1,
                    "column": 1,
                    "suggestion": "Usa solo los bloques de la caja.",
                }
            ],
        )
    adapted = adapt_workspace(workspace)
    _save_tree(attempt, workspace, adapted)
    errors = [item for item in adapted.diagnostics if item.severity == "error"]
    if adapted.program is None or errors:
        _remember(attempt, "comprobar", {"passed": False})
        return _bundle(attempt, passed=False, diagnostics=_named(concept, adapted.diagnostics))
    missing = _missing_blocks(workspace, _required(attempt.challenge))
    cases = []
    passed = True
    outputs: list[str] = []
    for case in attempt.challenge.test_cases.order_by("position"):
        result = _execute(adapted.program, adapted.source, list(case.inputs))
        ok = result.status == "completed" and result.output == case.expected_output
        if not ok:
            passed = False
        outputs.append(result.output)
        cases.append({"name": case.name, "kind": case.kind, "passed": ok, "output": result.output})
    if missing:
        passed = False
    _remember(attempt, "comprobar", {"passed": passed, "outputs": outputs})
    diagnostics = _named(concept, adapted.diagnostics)
    if missing:
        diagnostics.append(
            {
                "severity": "error",
                "code": "L0102",
                "message": f"{concept}: Falta un bloque que el reto pide.",
                "line": 1,
                "column": 1,
                "suggestion": None,
            }
        )
    return _bundle(attempt, passed=passed, cases=cases, diagnostics=diagnostics)


def run_prediction(user, attempt_id) -> dict[str, object]:
    attempt = _open_attempt(user, attempt_id)
    if attempt.challenge.activity_type != Challenge.PREDICT:
        raise DomainError("Este reto no se ejecuta así.")
    if not _razonar_correct(attempt):
        raise DomainError("Anticipa el valor antes de ejecutar.", code="conflict", status_code=409)
    restrictions = _restrictions(attempt.challenge)
    starter = restrictions.get("starter")
    if not isinstance(starter, dict):
        raise DomainError("El reto no tiene programa.")
    adapted = adapt_workspace(starter)
    if adapted.program is None:
        raise DomainError("No se pudo preparar el programa.")
    result = _execute(adapted.program, adapted.source, [])
    _remember(attempt, "comprobar", {"passed": True, "output": result.output})
    _save_tree(attempt, starter, adapted)
    return _bundle(attempt, output=result.output, source=adapted.source)


def expire_attempt(user, attempt_id) -> dict[str, object]:
    attempt = _owned_attempt(user, attempt_id)
    if attempt.status == ChallengeAttempt.OPEN and _late(attempt):
        _abandon(attempt)
    return _bundle(attempt)


@transaction.atomic
def close_attempt(user, attempt_id, reflection: object) -> dict[str, object]:
    attempt = _open_attempt(user, attempt_id)
    if _next(attempt) != "explicar":
        raise DomainError("Todavía no está resuelto.", code="conflict", status_code=409)
    if not isinstance(reflection, str) or len(reflection.strip()) < 12:
        raise DomainError("Explica el resultado con un poco más de detalle.")
    parts = _score_parts(attempt, reflection.strip())
    score = sum(parts.values())
    Reflection.objects.create(attempt=attempt, body=reflection.strip())
    attempt.status = ChallengeAttempt.COMPLETED
    attempt.score = score
    attempt.summary = _summary(parts, score)
    _stamp_elapsed(attempt)
    attempt.save(update_fields=["status", "score", "summary", "finished_at", "elapsed_seconds"])
    _mastery(user, attempt, score)
    _award_points(user, attempt)
    return _bundle(attempt)


def _award_points(user, attempt: ChallengeAttempt) -> None:
    repeated = (
        ChallengeAttempt.objects.filter(
            user=user,
            challenge=attempt.challenge,
            status=ChallengeAttempt.COMPLETED,
        )
        .exclude(pk=attempt.pk)
        .exists()
    )
    if repeated:
        return
    profile = Profile.objects.select_for_update().get(user=user)
    profile.points += attempt.challenge.points
    profile.save(update_fields=["points", "updated_at"])


def _existing_attempt(user, challenge: Challenge) -> ChallengeAttempt | None:
    rows = ChallengeAttempt.objects.filter(user=user, challenge=challenge).annotate(
        progress=Count("snapshots")
    )
    completed = (
        rows.filter(status=ChallengeAttempt.COMPLETED)
        .order_by("-finished_at", "-started_at")
        .first()
    )
    if completed is not None:
        return completed
    return rows.filter(status=ChallengeAttempt.OPEN).order_by("-progress", "-started_at").first()


def _path() -> LearningPath:
    path = LearningPath.objects.filter(name="Fundamentos", is_published=True).first()
    if path is None:
        raise DomainError("La ruta todavía no está publicada.", code="not_found", status_code=404)
    return path


def _sequence(path: LearningPath, user=None) -> list[Challenge]:
    if not PathEntry.objects.filter(path=path).exists():
        return list(
            Challenge.objects.filter(is_published=True, unit__path=path)
            .select_related("unit__concept")
            .order_by("unit__position", "position")
        )
    entries = list(
        PathEntry.objects.filter(path=path, challenge__is_published=True)
        .select_related("challenge__unit__concept")
        .order_by("position")
    )
    solved: set = set()
    if user is not None:
        withdrawn_ids = [entry.challenge_id for entry in entries if entry.withdrawn]
        if withdrawn_ids:
            solved = set(
                ChallengeAttempt.objects.filter(
                    user=user,
                    status=ChallengeAttempt.COMPLETED,
                    challenge_id__in=withdrawn_ids,
                ).values_list("challenge_id", flat=True)
            )
    return [
        entry.challenge
        for entry in entries
        if not entry.withdrawn or entry.challenge_id in solved
    ]


def _windows(path: LearningPath) -> dict:
    return {
        entry.challenge_id: (entry.opens_at, entry.closes_at)
        for entry in PathEntry.objects.filter(path=path)
    }


def _withdrawn_ids(path: LearningPath) -> set:
    return set(
        PathEntry.objects.filter(path=path, withdrawn=True).values_list("challenge_id", flat=True)
    )


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _on_path(path: LearningPath, challenge: Challenge, user=None) -> bool:
    return any(item.id == challenge.id for item in _sequence(path, user))


def _bound_path(user, challenge: Challenge, path_id: object) -> LearningPath:
    if path_id is None or path_id == "":
        path = challenge.unit.path
    else:
        try:
            path = LearningPath.objects.get(pk=path_id)
        except (LearningPath.DoesNotExist, ValueError, TypeError, ValidationError) as exc:
            raise DomainError("No se encontró la ruta.", code="not_found", status_code=404) from exc
    if not can_see_path(user, path) or not _on_path(path, challenge, user):
        raise DomainError("No se encontró el reto.", code="not_found", status_code=404)
    return path


def _published(challenge_id) -> Challenge:
    try:
        return Challenge.objects.select_related("unit__concept", "unit__path").get(
            pk=challenge_id, is_published=True, unit__path__is_published=True
        )
    except Challenge.DoesNotExist as exc:
        raise DomainError("No se encontró el reto.", code="not_found", status_code=404) from exc


def _ensure_open(user, challenge: Challenge, path: LearningPath) -> None:
    done = ChallengeAttempt.objects.filter(
        user=user, challenge=challenge, status=ChallengeAttempt.COMPLETED
    ).exists()
    if done:
        return
    opens_at, closes_at = _windows(path).get(challenge.id, (None, None))
    now = timezone.now()
    if opens_at is not None and now < opens_at:
        raise DomainError(
            "Este reto todavía no está disponible.",
            code="locked",
            status_code=403,
        )
    if closes_at is not None and now >= closes_at:
        raise DomainError(
            "El plazo de este reto ya terminó.",
            code="locked",
            status_code=403,
        )


def _ensure_unlocked(user, challenge: Challenge, path: LearningPath | None = None) -> None:
    chosen = path or challenge.unit.path
    if not can_see_path(user, chosen) or not _on_path(chosen, challenge, user):
        raise DomainError("No se encontró el reto.", code="not_found", status_code=404)
    if ChallengeAttempt.objects.filter(
        user=user, challenge=challenge, status=ChallengeAttempt.COMPLETED
    ).exists():
        return
    challenges = _sequence(chosen, user)
    index = next((i for i, item in enumerate(challenges) if item.id == challenge.id), None)
    if index is None:
        raise DomainError("No se encontró el reto.", code="not_found", status_code=404)
    windows = _windows(chosen)
    opens_at, closes_at = windows.get(challenge.id, (None, None))
    if opens_at is not None or closes_at is not None:
        return
    previous = None
    for item in challenges[:index]:
        item_opens, item_closes = windows.get(item.id, (None, None))
        if item_opens is None and item_closes is None:
            previous = item
    if previous is None:
        return
    done = ChallengeAttempt.objects.filter(
        user=user, challenge=previous, status=ChallengeAttempt.COMPLETED
    ).exists()
    if not done:
        raise DomainError(
            "Termina el reto anterior para abrir este.",
            code="locked",
            status_code=403,
        )


def _owned_attempt(user, attempt_id) -> ChallengeAttempt:
    try:
        return ChallengeAttempt.objects.select_related(
            "challenge__unit__concept", "challenge__unit__path"
        ).get(pk=attempt_id, user=user)
    except ChallengeAttempt.DoesNotExist as exc:
        raise DomainError("No se encontró el intento.", code="not_found", status_code=404) from exc


def _open_attempt(user, attempt_id) -> ChallengeAttempt:
    attempt = _owned_attempt(user, attempt_id)
    if attempt.status == ChallengeAttempt.OPEN and _late(attempt):
        _abandon(attempt)
    if attempt.status != ChallengeAttempt.OPEN:
        if attempt.summary == "Se agotó el tiempo.":
            raise DomainError(
                "Se agotó el tiempo de este intento.", code="conflict", status_code=409
            )
        raise DomainError("Este intento ya está cerrado.", code="conflict", status_code=409)
    return attempt


def _limit_seconds(challenge: Challenge) -> int | None:
    value = challenge.time_limit_seconds
    if isinstance(value, int) and value > 0:
        return value
    return None


def _seconds_left(attempt: ChallengeAttempt) -> int | None:
    limit = _limit_seconds(attempt.challenge)
    if limit is None or attempt.status != ChallengeAttempt.OPEN:
        return None
    elapsed = (timezone.now() - attempt.started_at).total_seconds()
    remaining = limit - elapsed
    if remaining <= 0:
        return 0
    return math.ceil(remaining)


def _late(attempt: ChallengeAttempt) -> bool:
    return _seconds_left(attempt) == 0


def _stamp_elapsed(attempt: ChallengeAttempt) -> None:
    finished = timezone.now()
    attempt.finished_at = finished
    attempt.elapsed_seconds = max(0, int((finished - attempt.started_at).total_seconds()))


def _abandon(attempt: ChallengeAttempt) -> None:
    attempt.status = ChallengeAttempt.ABANDONED
    attempt.summary = "Se agotó el tiempo."
    _stamp_elapsed(attempt)
    attempt.save(update_fields=["status", "summary", "finished_at", "elapsed_seconds"])


def _restrictions(challenge: Challenge) -> dict[str, Any]:
    data = challenge.restrictions
    return data if isinstance(data, dict) else {}


def _public_challenge(challenge: Challenge) -> dict[str, object]:
    restrictions = _restrictions(challenge)
    activity = challenge.activity_type
    task: dict[str, object]
    if activity == Challenge.CLASSIFY:
        items = restrictions.get("items")
        rows = items if isinstance(items, list) else []
        task = {
            "categories": restrictions.get("categories") or [],
            "items": [
                {"id": item["id"], "text": item["text"]}
                for item in rows
                if isinstance(item, dict) and "category" in item
            ],
        }
    elif activity == Challenge.ORDER:
        items = restrictions.get("items")
        rows = items if isinstance(items, list) else []
        task = {
            "items": [
                {"id": item["id"], "text": item["text"]} for item in rows if isinstance(item, dict)
            ]
        }
    elif activity == Challenge.BUILD:
        tools = restrictions.get("tools")
        task = {
            "question": restrictions.get("question") or "",
            "tools": tools if isinstance(tools, list) and tools else ["bloques"],
            "cases": [
                {
                    "name": case.name,
                    "inputs": list(case.inputs),
                    "expected_output": case.expected_output,
                }
                for case in challenge.test_cases.order_by("position")
            ],
        }
    else:
        starter = restrictions.get("starter")
        source = ""
        if isinstance(starter, dict):
            source = adapt_workspace(starter).source
        task = {"question": restrictions.get("question") or "", "source": source}
    return {
        "id": str(challenge.id),
        "title": challenge.title,
        "prompt": challenge.prompt,
        "activity_type": activity,
        "difficulty": challenge.difficulty,
        "points": challenge.points,
        "concept": challenge.unit.concept.name,
        "allowed_blocks": list(challenge.allowed_blocks),
        "time_limit_seconds": challenge.time_limit_seconds,
        "task": task,
    }


def _bundle(attempt: ChallengeAttempt, **extra: object) -> dict[str, object]:
    challenge = attempt.challenge
    standing = standing_of(attempt.user)
    payload: dict[str, object] = {
        "challenge": _public_challenge(challenge),
        "attempt": _state(attempt),
        "history": _history(attempt.user, challenge),
        "points": standing["points"],
        "rank": standing["rank"],
    }
    payload.update(extra)
    return payload


def _solution_next(attempt: ChallengeAttempt) -> bool:
    used = set(attempt.hint_usages.values_list("hint_id", flat=True))
    remaining = [
        hint
        for hint in attempt.challenge.hints.order_by("level", "position")
        if hint.id not in used
    ]
    return len(remaining) == 1 and _SOLUTION_MARK in remaining[0].body


def _state(attempt: ChallengeAttempt) -> dict[str, object]:
    hints = [
        {
            "level": usage.hint.level,
            "body": usage.hint.body,
            "solution": _SOLUTION_MARK in usage.hint.body,
        }
        for usage in attempt.hint_usages.select_related("hint").order_by("created_at")
    ]
    prediction = attempt.predictions.order_by("-created_at").first()
    try:
        reflection = attempt.reflection.body
    except Reflection.DoesNotExist:
        reflection = None
    return {
        "id": str(attempt.id),
        "status": attempt.status,
        "score": attempt.score,
        "summary": attempt.summary,
        "next_stage": "cerrado" if attempt.status != ChallengeAttempt.OPEN else _next(attempt),
        "hints": hints,
        "hints_left": attempt.challenge.hints.count() - len(hints),
        "solution_next": _solution_next(attempt),
        "prediction": (
            None
            if prediction is None
            else {"answer": prediction.answer, "is_correct": prediction.is_correct}
        ),
        "reflection": reflection,
        "time_limit_seconds": attempt.challenge.time_limit_seconds,
        "seconds_left": _seconds_left(attempt),
        "elapsed_seconds": attempt.elapsed_seconds,
        "finished_at": None if attempt.finished_at is None else attempt.finished_at.isoformat(),
    }


def _history(user, challenge: Challenge) -> list[dict[str, object]]:
    rows = ChallengeAttempt.objects.filter(
        user=user,
        challenge=challenge,
        status__in=[ChallengeAttempt.COMPLETED, ChallengeAttempt.ABANDONED],
    ).order_by("started_at")
    history: list[dict[str, object]] = []
    for number, row in enumerate(rows, start=1):
        history.append(
            {
                "id": str(row.id),
                "number": number,
                "status": row.status,
                "score": row.score,
                "elapsed_seconds": row.elapsed_seconds,
                "finished_at": None if row.finished_at is None else row.finished_at.isoformat(),
                "summary": row.summary,
            }
        )
    return history


def _latest(attempt: ChallengeAttempt, stage: str) -> dict[str, Any] | None:
    found: dict[str, Any] | None = None
    best = -1
    for snap in attempt.snapshots.filter(schema_version=2):
        data = snap.blockly_json
        if not isinstance(data, dict) or data.get("stage") != stage:
            continue
        mark = data.get("mark")
        if isinstance(mark, int) and mark >= best:
            best = mark
            found = data
    return found


def _has(attempt: ChallengeAttempt, stage: str) -> bool:
    return _latest(attempt, stage) is not None


def _remember(attempt: ChallengeAttempt, stage: str, answer: object) -> None:
    WorkspaceSnapshot.objects.create(
        attempt=attempt,
        schema_version=2,
        blockly_json={"stage": stage, "answer": answer, "mark": time.time_ns()},
    )


def _next(attempt: ChallengeAttempt) -> str:
    activity = attempt.challenge.activity_type
    if not _has(attempt, "comprender"):
        return "comprender"
    if not _razonar_correct(attempt):
        return "razonar"
    if activity == Challenge.BUILD:
        check = _latest(attempt, "comprobar")
        if check is None:
            return "construir"
        answer = check.get("answer")
        if not isinstance(answer, dict) or answer.get("passed") is not True:
            return "comprobar"
    elif activity == Challenge.PREDICT:
        check = _latest(attempt, "comprobar")
        if check is None:
            return "comprobar"
    return "explicar"


def _razonar_correct(attempt: ChallengeAttempt) -> bool:
    saved = _latest(attempt, "razonar")
    if saved is None:
        return False
    return _grade_answer(attempt.challenge, saved.get("answer"))


def _prediction_correct(attempt: ChallengeAttempt) -> bool:
    return attempt.predictions.filter(is_correct=True).exists()


def _grade_answer(challenge: Challenge, answer: object) -> bool:
    restrictions = _restrictions(challenge)
    if challenge.activity_type == Challenge.CLASSIFY:
        if not isinstance(answer, dict):
            return False
        choices = answer.get("choices")
        if not isinstance(choices, dict):
            return False
        items = restrictions.get("items")
        if not isinstance(items, list):
            return False
        expected = {
            item["id"]: item["category"]
            for item in items
            if isinstance(item, dict) and "id" in item and "category" in item
        }
        return {str(key): value for key, value in choices.items()} == expected
    if challenge.activity_type == Challenge.ORDER:
        if not isinstance(answer, dict):
            return False
        order = answer.get("order")
        if not isinstance(order, list):
            return False
        return [str(item) for item in order] == list(restrictions.get("solution") or [])
    text = ""
    if isinstance(answer, dict) and isinstance(answer.get("text"), str):
        text = answer["text"]
    elif isinstance(answer, str):
        text = answer
    accepted = restrictions.get("accepted")
    if not isinstance(accepted, list):
        return False
    token = _normalize(text)
    return token in {_normalize(str(item)) for item in accepted}


def _normalize(text: str) -> str:
    return "".join(text.strip().casefold().split())


def _store_prediction(attempt: ChallengeAttempt, text: str, correct: bool) -> None:
    restrictions = _restrictions(attempt.challenge)
    accepted = restrictions.get("accepted")
    expected = str(accepted[0]) if isinstance(accepted, list) and accepted else ""
    Prediction.objects.create(
        attempt=attempt,
        prompt_key="valor",
        expected=expected,
        answer=text.strip(),
        is_correct=correct,
    )


def _required(challenge: Challenge) -> list[str]:
    value = _restrictions(challenge).get("required_blocks")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _block_types(node: object) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        kind = node.get("type")
        if isinstance(kind, str) and kind.startswith("traza_"):
            found.add(kind)
        for value in node.values():
            found |= _block_types(value)
    elif isinstance(node, list):
        for item in node:
            found |= _block_types(item)
    return found


def _foreign_blocks(workspace: dict[str, Any], allowed: list[str]) -> bool:
    if not allowed:
        return False
    return not _block_types(workspace) <= set(allowed)


def _missing_blocks(workspace: dict[str, Any], required: list[str]) -> bool:
    present = _block_types(workspace)
    return any(block not in present for block in required)


def _named(concept: str, diagnostics) -> list[dict[str, object]]:
    named: list[dict[str, object]] = []
    for item in diagnostics:
        body = diagnostic_payload(item)
        if body["severity"] == "error":
            body["message"] = f"{concept}: {body['message']}"
        named.append(body)
    return named


def _execute(program, source: str, inputs: list[str]):
    limits = Limits.from_profile(STRICT)
    interpreter = Interpreter(
        program,
        source,
        STRICT,
        limits,
        Cancellation(),
        time.monotonic,
        random.Random(0),
    )
    return drive(interpreter.run(), inputs, (), interpreter.cells)


def _save_tree(attempt: ChallengeAttempt, workspace: dict[str, Any], adapted) -> None:
    WorkspaceSnapshot.objects.create(
        attempt=attempt,
        schema_version=1,
        blockly_json=workspace,
        ast_dump="" if adapted.program is None else dump(adapted.program),
        pseudocode=adapted.source,
        bindings=[
            {"block_id": item.block_id, "line": item.line, "column": item.column}
            for item in adapted.bindings
        ],
    )


def _score_parts(attempt: ChallengeAttempt, reflection: str) -> dict[str, int]:
    levels = list(attempt.hint_usages.values_list("hint__level", flat=True))
    if any(level >= 5 for level in levels):
        autonomy = 0
    else:
        autonomy = {0: 10, 1: 6, 2: 3}.get(len(levels), 0)
    return {
        "comprension": _WEIGHTS["comprension"],
        "diseno": _WEIGHTS["diseno"],
        "correccion": _WEIGHTS["correccion"],
        "explicacion": _WEIGHTS["explicacion"] if len(reflection) >= 12 else 0,
        "autonomia": autonomy,
    }


def _summary(parts: dict[str, int], score: int) -> str:
    return (
        f"Puntuación {score}. Comprensión {parts['comprension']}, "
        f"diseño {parts['diseno']}, corrección {parts['correccion']}, "
        f"explicación {parts['explicacion']}, autonomía {parts['autonomia']}."
    )


def _mastery(user, attempt: ChallengeAttempt, score: int) -> None:
    concept = attempt.challenge.unit.concept
    level = min(5, attempt.challenge.difficulty)
    current = ConceptMastery.objects.filter(user=user, concept=concept).first()
    if current is not None and current.level >= level:
        current.evidence = {"attempt": str(attempt.id), "score": score}
        current.save(update_fields=["evidence", "updated_at"])
        return
    ConceptMastery.objects.update_or_create(
        user=user,
        concept=concept,
        defaults={"level": level, "evidence": {"attempt": str(attempt.id), "score": score}},
    )
