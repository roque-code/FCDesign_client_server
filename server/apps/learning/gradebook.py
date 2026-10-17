"""Progreso de los estudiantes: una fila por alumno y una columna por problema."""

from __future__ import annotations

import csv
import io
import unicodedata

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Profile
from apps.learning.models import Challenge, ChallengeAttempt, LearningPath, PathEntry
from apps.learning.progress import visible_paths
from apps.learning.roster import _communities_of, _member_ids, _require_teacher
from config.errors import DomainError

NOT_FOUND = "not_found"
_LABELS = {
    "es": {
        "name": "Nombre",
        "email": "Correo",
        "communities": "Comunidades",
        "grade": "Nota",
        "from": "desde",
        "until": "hasta",
    },
    "en": {
        "name": "Name",
        "email": "Email",
        "communities": "Communities",
        "grade": "Grade",
        "from": "from",
        "until": "until",
    },
}


def gradebook_csv(teacher, path_id, lang: str) -> tuple[str, str]:
    _require_teacher(teacher)
    labels = _LABELS["en" if lang == "en" else "es"]
    path, on_path = _cohort(teacher, path_id)
    if path is None:
        raise DomainError("No se encontró la ruta.", code=NOT_FOUND, status_code=404)
    activities = _activities(path, [student.pk for student in on_path])
    scores = _scores([student.pk for student in on_path], [item[0].pk for item in activities])
    communities = _communities_of(teacher)
    headers = [
        labels["name"],
        labels["email"],
        labels["communities"],
        labels["grade"],
        *_problem_headers(activities, labels),
    ]
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, dialect="excel", lineterminator="\r\n")
    writer.writerow(headers)
    for student in on_path:
        earned = [scores.get((student.pk, challenge.pk)) for challenge, _, _ in activities]
        writer.writerow(
            [
                student.profile.display_name,
                student.email,
                " | ".join(communities.get(student.pk, [])),
                _grade(earned),
                *[_cell(score) for score in earned],
            ]
        )
    return _filename(path.name), buffer.getvalue()


def _students(teacher) -> list:
    user_ids = _member_ids(teacher)
    return [
        user
        for user in get_user_model()
        .objects.filter(pk__in=user_ids)
        .select_related("profile")
        .order_by("profile__display_name", "email")
        if user.profile.role == Profile.STUDENT
    ]


def _cohort(teacher, path_id) -> tuple[LearningPath | None, list]:
    chosen: LearningPath | None = None
    visible: list[tuple[object, list[LearningPath]]] = []
    for student in _students(teacher):
        paths = visible_paths(student)
        visible.append((student, paths))
        if chosen is None:
            chosen = next((path for path in paths if str(path.id) == str(path_id)), None)
    if chosen is None:
        return None, []
    return chosen, [
        student for student, paths in visible if any(path.id == chosen.id for path in paths)
    ]


def _activities(path: LearningPath, user_ids: list[int]) -> list[tuple[Challenge, object, object]]:
    entries = list(
        PathEntry.objects.filter(path=path, challenge__is_published=True)
        .select_related("challenge")
        .order_by("position")
    )
    if entries:
        solved = _solved(user_ids, [entry.challenge_id for entry in entries if entry.withdrawn])
        return [
            (entry.challenge, entry.opens_at, entry.closes_at)
            for entry in entries
            if not entry.withdrawn or entry.challenge_id in solved
        ]
    rows = Challenge.objects.filter(is_published=True, unit__path=path).order_by(
        "unit__position", "position"
    )
    return [(challenge, None, None) for challenge in rows]


def _solved(user_ids: list[int], challenge_ids: list) -> set:
    if not user_ids or not challenge_ids:
        return set()
    return set(
        ChallengeAttempt.objects.filter(
            user_id__in=user_ids,
            challenge_id__in=challenge_ids,
            status=ChallengeAttempt.COMPLETED,
        ).values_list("challenge_id", flat=True)
    )


def _scores(user_ids: list[int], challenge_ids: list) -> dict[tuple[int, object], int]:
    found: dict[tuple[int, object], int] = {}
    if not user_ids or not challenge_ids:
        return found
    rows = ChallengeAttempt.objects.filter(
        user_id__in=user_ids,
        challenge_id__in=challenge_ids,
        status=ChallengeAttempt.COMPLETED,
    ).order_by("-finished_at", "-started_at")
    for row in rows:
        if row.score is None:
            continue
        found.setdefault((row.user_id, row.challenge_id), row.score)
    return found


def _problem_headers(activities, labels: dict[str, str]) -> list[str]:
    seen: dict[str, int] = {}
    headers: list[str] = []
    for challenge, opens_at, closes_at in activities:
        label = _problem_label(challenge.title, opens_at, closes_at, labels)
        count = seen.get(label, 0) + 1
        seen[label] = count
        headers.append(label if count == 1 else f"{label} · {count}")
    return headers


def _problem_label(title: str, opens_at, closes_at, labels: dict[str, str]) -> str:
    start = _day(opens_at)
    end = _day(closes_at)
    if start and end:
        window = f"{start} – {end}"
    elif start:
        window = f"{labels['from']} {start}"
    elif end:
        window = f"{labels['until']} {end}"
    else:
        window = ""
    if window:
        return f"{title} · {window} · 100"
    return f"{title} · 100"


def _day(value) -> str:
    if value is None:
        return ""
    return timezone.localtime(value).strftime("%Y-%m-%d")


def _cell(score: int | None) -> str:
    if score is None:
        return ""
    return str(score)


def _grade(scores: list[int | None]) -> str:
    if not scores:
        return ""
    total = sum(score or 0 for score in scores)
    count = len(scores)
    return str((total + count // 2) // count)


def _filename(name: str) -> str:
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(char if char.isalnum() else "-" for char in folded.lower())
    cleaned = "-".join(part for part in cleaned.split("-") if part)[:60] or "ruta"
    return f"progreso-{cleaned}.csv"
