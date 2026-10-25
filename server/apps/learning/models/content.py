"""Rutas, unidades, retos, casos y pistas. El contenido de sistema no tiene dueño."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class LearningPath(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    position = models.PositiveIntegerField()
    is_published = models.BooleanField(default=False)
    is_bank = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="learning_paths",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="uniq_learning_path_name"),
            models.UniqueConstraint(fields=["position"], name="uniq_learning_path_position"),
        ]

    def __str__(self) -> str:
        return self.name


class LearningUnit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name="units")
    title = models.CharField(max_length=120)
    concept = models.ForeignKey(
        "learning.Concept",
        on_delete=models.PROTECT,
        related_name="units",
    )
    position = models.PositiveIntegerField()
    prerequisite = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="dependents",
    )

    class Meta:
        ordering = ["path", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["path", "position"], name="uniq_learning_unit_position"
            ),
            models.UniqueConstraint(fields=["path", "title"], name="uniq_learning_unit_title"),
        ]

    def __str__(self) -> str:
        return self.title


class Challenge(models.Model):
    CLASSIFY = "classify"
    ORDER = "order"
    BUILD = "build"
    PREDICT = "predict"
    ACTIVITY_TYPES = (CLASSIFY, ORDER, BUILD, PREDICT)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(LearningUnit, on_delete=models.CASCADE, related_name="challenges")
    title = models.CharField(max_length=120)
    prompt = models.TextField()
    activity_type = models.CharField(max_length=16)
    difficulty = models.PositiveSmallIntegerField()
    points = models.PositiveSmallIntegerField(default=10)
    time_limit_seconds = models.PositiveIntegerField(null=True, blank=True)
    allowed_blocks = models.JSONField(default=list)
    restrictions = models.JSONField(default=dict)
    weights = models.JSONField(default=dict)
    position = models.PositiveIntegerField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["unit", "position"]
        constraints = [
            models.UniqueConstraint(fields=["unit", "position"], name="uniq_challenge_position"),
            models.UniqueConstraint(fields=["unit", "title"], name="uniq_challenge_title"),
            models.CheckConstraint(
                condition=Q(activity_type__in=["classify", "order", "build", "predict"]),
                name="challenge_activity_type",
            ),
            models.CheckConstraint(
                condition=Q(difficulty__gte=1, difficulty__lte=5),
                name="challenge_difficulty",
            ),
            models.CheckConstraint(
                condition=Q(points__gte=1, points__lte=500),
                name="challenge_points",
            ),
            models.CheckConstraint(
                condition=Q(time_limit_seconds__isnull=True)
                | Q(time_limit_seconds__gte=1, time_limit_seconds__lte=86400),
                name="challenge_time_limit",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class ChallengeTestCase(models.Model):
    NORMAL = "normal"
    BOUNDARY = "boundary"
    INVALID = "invalid"
    KINDS = (NORMAL, BOUNDARY, INVALID)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="test_cases")
    name = models.CharField(max_length=80)
    inputs = models.JSONField(default=list)
    expected_output = models.TextField(blank=True)
    kind = models.CharField(max_length=16)
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["challenge", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "position"],
                name="uniq_challenge_case_position",
            ),
            models.UniqueConstraint(fields=["challenge", "name"], name="uniq_challenge_case_name"),
            models.CheckConstraint(
                condition=Q(kind__in=["normal", "boundary", "invalid"]),
                name="challenge_case_kind",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Hint(models.Model):
    """Niveles 1 a 5: orientación, pregunta, señalamiento, demostración parcial y solución."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="hints")
    level = models.PositiveSmallIntegerField()
    body = models.TextField()
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["challenge", "level", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["challenge", "level", "position"],
                name="uniq_hint_level_position",
            ),
            models.CheckConstraint(
                condition=Q(level__gte=1, level__lte=5),
                name="hint_level_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.level}: {self.body[:40]}"


class PathEntry(models.Model):
    """Un reto del catálogo colocado en una ruta del docente."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name="entries")
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name="path_entries")
    position = models.PositiveIntegerField()
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    withdrawn = models.BooleanField(default=False)
    weights = models.JSONField(default=dict)

    class Meta:
        ordering = ["path", "position"]
        constraints = [
            models.UniqueConstraint(fields=["path", "position"], name="uniq_path_entry_position"),
            models.UniqueConstraint(fields=["path", "challenge"], name="uniq_path_entry_challenge"),
        ]

    def __str__(self) -> str:
        return f"{self.position}"


class PathAssignment(models.Model):
    """La ruta llega a una comunidad entera o a un alumno de una comunidad del docente."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    path = models.ForeignKey(LearningPath, on_delete=models.CASCADE, related_name="assignments")
    community = models.ForeignKey(
        "classroom.Community",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="path_assignments",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="path_assignments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(community__isnull=False, student__isnull=True)
                    | Q(community__isnull=True, student__isnull=False)
                ),
                name="path_assignment_target",
            ),
            models.UniqueConstraint(
                fields=["path", "community"],
                condition=Q(community__isnull=False),
                name="uniq_path_community",
            ),
            models.UniqueConstraint(
                fields=["path", "student"],
                condition=Q(student__isnull=False),
                name="uniq_path_student",
            ),
        ]

    def __str__(self) -> str:
        return str(self.path_id)
