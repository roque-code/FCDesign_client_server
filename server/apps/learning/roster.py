"""Avance que un docente lee de las cuentas que ya puede ver en sus comunidades."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Count, Max

from apps.accounts.models import Profile
from apps.accounts.services import standing_of
from apps.classroom.models import Membership
from apps.learning.models import Challenge, ChallengeAttempt, ConceptMastery, PathEntry, Reflection
from apps.learning.progress import (
    _language_public,
    _next,
    _public_challenge,
    _sequence,
    _solution,
    path_payload,
    visible_paths,
)
from config.errors import DomainError

NOT_FOUND = "not_found"


def _require_teacher(user) -> None:
    if user.profile.role != Profile.TEACHER:
        raise DomainError("Solo un docente puede ver el avance.", status_code=403)


def _member_ids(teacher) -> list[int]:
    return list(
        Membership.objects.filter(community__owner=teacher)
        .values_list("user_id", flat=True)
        .distinct()
    )


def _communities_of(teacher) -> dict[int, list[str]]:
    grouped: dict[int, list[str]] = {}
    rows = (
        Membership.objects.filter(community__owner=teacher)
        .order_by("community__name")
        .values_list("user_id", "community__name")
    )
    for user_id, name in rows:
        names = grouped.setdefault(user_id, [])
        if name not in names:
            names.append(name)
    return grouped


def _progress_rows(user_ids: list[int]) -> dict[int, dict[str, object]]:
    if not user_ids:
        return {}
    rows = (
        ChallengeAttempt.objects.filter(
            user_id__in=user_ids,
            status=ChallengeAttempt.COMPLETED,
            challenge__is_published=True,
            challenge__unit__path__is_published=True,
        )
        .values("user_id")
        .annotate(total=Count("challenge_id", distinct=True), last=Max("finished_at"))
    )
    return {
        row["user_id"]: {
            "completed": int(row["total"]),
            "last_activity": None if row["last"] is None else row["last"].isoformat(),
        }
        for row in rows
    }


def _person(
    user, communities: list[str], progress: dict[str, object], total: int
) -> dict[str, object]:
    standing = standing_of(user)
    return {
        "id": user.pk,
        "display_name": user.profile.display_name,
        "email": user.email,
        "role": user.profile.role,
        "points": standing["points"],
        "rank": standing["rank"],
        "completed": progress.get("completed", 0),
        "total": total,
        "last_activity": progress.get("last_activity"),
        "communities": communities,
        "routes": [{"id": str(path.id), "name": path.name} for path in visible_paths(user)],
    }


def _route_activity(path, user_ids: list[int]) -> dict[int, dict[str, object]]:
    offered = {item.id for item in _sequence(path)}
    withdrawn = set(
        PathEntry.objects.filter(
            path=path, withdrawn=True, challenge__is_published=True
        ).values_list("challenge_id", flat=True)
    )
    if not user_ids:
        return {}
    relevant = offered | withdrawn
    done: dict[int, set] = {user_id: set() for user_id in user_ids}
    last: dict[int, object] = {}
    if relevant:
        rows = ChallengeAttempt.objects.filter(
            user_id__in=user_ids,
            challenge_id__in=relevant,
            status=ChallengeAttempt.COMPLETED,
        ).values_list("user_id", "challenge_id", "finished_at")
        for user_id, challenge_id, finished in rows:
            done[user_id].add(challenge_id)
            current = last.get(user_id)
            if finished is not None and (current is None or finished > current):
                last[user_id] = finished
    result: dict[int, dict[str, object]] = {}
    for user_id in user_ids:
        kept = done[user_id] & withdrawn
        visible = offered | kept
        finished = last.get(user_id)
        result[user_id] = {
            "completed": len(done[user_id] & visible),
            "total": len(visible),
            "last_activity": None if finished is None else finished.isoformat(),
        }
    return result


def roster_payload(teacher) -> dict[str, object]:
    _require_teacher(teacher)
    user_ids = _member_ids(teacher)
    users = [
        user
        for user in get_user_model()
        .objects.filter(pk__in=user_ids)
        .select_related("profile")
        .order_by("profile__display_name", "email")
        if user.profile.role == Profile.STUDENT
    ]
    communities = _communities_of(teacher)
    grouped: dict[str, dict[str, object]] = {}
    for user in users:
        standing = standing_of(user)
        for path in visible_paths(user):
            key = str(path.id)
            bucket = grouped.get(key)
            if bucket is None:
                bucket = {
                    "id": key,
                    "name": path.name,
                    "description": path.description,
                    "position": path.position,
                    "path": path,
                    "students": [],
                }
                grouped[key] = bucket
            students = bucket["students"]
            assert isinstance(students, list)
            students.append(
                {
                    "id": user.pk,
                    "display_name": user.profile.display_name,
                    "email": user.email,
                    "communities": communities.get(user.pk, []),
                    "completed": 0,
                    "total": 0,
                    "points": standing["points"],
                    "rank": standing["rank"],
                    "last_activity": None,
                }
            )
    routes: list[dict[str, object]] = []
    ordered = sorted(
        grouped.values(), key=lambda item: (item["position"], str(item["name"]).casefold())
    )
    for bucket in ordered:
        path = bucket.pop("path")
        bucket.pop("position")
        students = bucket["students"]
        assert isinstance(students, list)
        activity = _route_activity(path, [int(item["id"]) for item in students])
        for student in students:
            assert isinstance(student, dict)
            row = activity.get(student["id"], {})
            student["completed"] = row.get("completed", 0)
            student["total"] = row.get("total", 0)
            student["last_activity"] = row.get("last_activity")
        routes.append(bucket)
    return {"routes": routes, "communities": _community_choices(teacher)}


def _community_choices(teacher) -> list[dict[str, object]]:
    choices: list[dict[str, object]] = []
    owned = teacher.communities.order_by("name")
    for community in owned:
        students = community.memberships.exclude(user__profile__role=Profile.TEACHER).count()
        choices.append(
            {
                "id": str(community.id),
                "name": community.name,
                "student_count": students,
            }
        )
    return choices


def _scored_path(member, path, scores: dict[str, int | None]) -> dict[str, object]:
    payload = path_payload(member, path)
    challenges = payload["challenges"]
    assert isinstance(challenges, list)
    for item in challenges:
        assert isinstance(item, dict)
        item["score"] = scores.get(str(item["id"]))
    done = sum(
        1 for item in challenges if isinstance(item, dict) and item.get("state") == "completed"
    )
    return {
        "id": payload["id"],
        "name": payload["name"],
        "description": payload["description"],
        "completed": done,
        "total": len(challenges),
        "challenges": challenges,
    }


def member_progress(teacher, user_id: int) -> dict[str, object]:
    _require_teacher(teacher)
    if user_id not in set(_member_ids(teacher)):
        raise DomainError("No se encontró a esa persona.", code=NOT_FOUND, status_code=404)
    member = get_user_model().objects.select_related("profile").get(pk=user_id)
    scores: dict[str, int | None] = {}
    attempts = ChallengeAttempt.objects.filter(user=member).order_by("-started_at")
    for attempt in attempts:
        scores.setdefault(str(attempt.challenge_id), attempt.score)
    paths = [_scored_path(member, path, scores) for path in visible_paths(member)]
    mastery = [
        {"concept": row.concept.name, "level": row.level}
        for row in ConceptMastery.objects.filter(user=member)
        .select_related("concept")
        .order_by("concept__name")
    ]
    communities = _communities_of(teacher).get(member.pk, [])
    progress = _progress_rows([member.pk]).get(member.pk, {})
    return {
        "person": _person(member, communities, progress, sum(int(item["total"]) for item in paths)),
        "paths": paths,
        "mastery": mastery,
    }


def member_work(teacher, user_id: int, challenge_id) -> dict[str, object]:
    _require_teacher(teacher)
    if user_id not in set(_member_ids(teacher)):
        raise DomainError("No se encontró a esa persona.", code=NOT_FOUND, status_code=404)
    member = get_user_model().objects.select_related("profile").get(pk=user_id)
    try:
        challenge = Challenge.objects.select_related("unit__concept").get(
            pk=challenge_id, is_published=True
        )
    except Challenge.DoesNotExist as exc:
        raise DomainError("No se encontró el reto.", code=NOT_FOUND, status_code=404) from exc
    attempt = (
        ChallengeAttempt.objects.filter(user=member, challenge=challenge)
        .order_by("-started_at")
        .first()
    )
    if attempt is None and not _on_visible_path(member, challenge):
        raise DomainError("No se encontró el reto.", code=NOT_FOUND, status_code=404)
    return {
        "challenge": _public_challenge(challenge),
        "attempt": None if attempt is None else _attempt_work(challenge, attempt),
    }


def _on_visible_path(member, challenge: Challenge) -> bool:
    target = str(challenge.id)
    for path in visible_paths(member):
        payload = path_payload(member, path)
        challenges = payload["challenges"]
        assert isinstance(challenges, list)
        if any(isinstance(item, dict) and item.get("id") == target for item in challenges):
            return True
    return False


def _attempt_work(challenge: Challenge, attempt: ChallengeAttempt) -> dict[str, object]:
    razonar, comprobar = _saved_stages(attempt)
    prediction = attempt.predictions.order_by("-created_at").first()
    try:
        reflection = attempt.reflection.body
    except Reflection.DoesNotExist:
        reflection = None
    answer = _answer_lines(challenge, razonar)
    if prediction is not None and len(answer) == 1 and answer[0]["value"] == prediction.answer:
        answer = []
    code = (
        attempt.snapshots.filter(schema_version=1)
        .exclude(pseudocode="")
        .order_by("-created_at")
        .values_list("pseudocode", flat=True)
        .first()
    )
    payload: dict[str, object] = {
        "status": attempt.status,
        "score": attempt.score,
        "summary": attempt.summary,
        "next_stage": "cerrado" if attempt.status != ChallengeAttempt.OPEN else _next(attempt),
        "elapsed_seconds": attempt.elapsed_seconds,
        "finished_at": None if attempt.finished_at is None else attempt.finished_at.isoformat(),
        "reflection": reflection,
        "prediction": (
            None
            if prediction is None
            else {"answer": prediction.answer, "is_correct": prediction.is_correct}
        ),
        "answer": answer,
        "source": code or "",
        "cases": _case_rows(challenge, comprobar),
    }
    solution = _solution(attempt, only_completed=False)
    if solution is not None:
        payload["solution"] = solution
    language = _language_public(attempt)
    if language is not None:
        payload["language"] = language
    return payload


def _saved_stages(attempt: ChallengeAttempt) -> tuple[object, object]:
    razonar = None
    comprobar = None
    rows = attempt.snapshots.filter(schema_version=2).order_by("-created_at")
    for row in rows:
        payload = row.blockly_json
        if not isinstance(payload, dict):
            continue
        stage = payload.get("stage")
        if stage == "razonar" and razonar is None:
            razonar = payload.get("answer")
        elif stage == "comprobar" and comprobar is None:
            comprobar = payload.get("answer")
        if razonar is not None and comprobar is not None:
            break
    return razonar, comprobar


def _answer_lines(challenge: Challenge, answer: object) -> list[dict[str, str]]:
    restrictions = challenge.restrictions if isinstance(challenge.restrictions, dict) else {}
    labels = _item_labels(restrictions.get("items"))
    if challenge.activity_type == Challenge.CLASSIFY and isinstance(answer, dict):
        choices = answer.get("choices")
        if not isinstance(choices, dict):
            return []
        return [
            {"label": labels.get(str(key), str(key)), "value": str(value)}
            for key, value in choices.items()
            if isinstance(value, str)
        ]
    if challenge.activity_type == Challenge.ORDER and isinstance(answer, dict):
        order = answer.get("order")
        if not isinstance(order, list):
            return []
        return [
            {"label": str(index), "value": labels.get(str(item), str(item))}
            for index, item in enumerate(order, start=1)
        ]
    text = ""
    if isinstance(answer, dict) and isinstance(answer.get("text"), str):
        text = answer["text"].strip()
    elif isinstance(answer, str):
        text = answer.strip()
    if text == "":
        return []
    return [{"label": "Respuesta", "value": text}]


def _item_labels(items: object) -> dict[str, str]:
    labels: dict[str, str] = {}
    if not isinstance(items, list):
        return labels
    for item in items:
        if isinstance(item, dict) and "id" in item:
            labels[str(item["id"])] = str(item.get("text") or item["id"])
    return labels


def _case_rows(challenge: Challenge, answer: object) -> list[dict[str, object]]:
    if not isinstance(answer, dict):
        return []
    outputs = answer.get("outputs")
    if not isinstance(outputs, list):
        return []
    rows: list[dict[str, object]] = []
    cases = list(challenge.test_cases.order_by("position"))
    for index, case in enumerate(cases):
        output = outputs[index] if index < len(outputs) and isinstance(outputs[index], str) else ""
        rows.append(
            {
                "name": case.name,
                "passed": output == case.expected_output,
                "output": output,
            }
        )
    return rows
