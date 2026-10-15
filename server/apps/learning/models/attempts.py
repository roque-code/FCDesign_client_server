"""Intentos del alumno. No son ejecuciones del banco de trabajo."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class ChallengeAttempt(models.Model):
    OPEN = "open"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    STATUSES = (OPEN, COMPLETED, ABANDONED)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    challenge = models.ForeignKey(
        "learning.Challenge",
        on_delete=models.PROTECT,
        related_name="attempts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="learning_attempts",
    )
    status = models.CharField(max_length=16, default=OPEN)
    score = models.PositiveSmallIntegerField(null=True, blank=True)
    summary = models.TextField(blank=True)
    elapsed_seconds = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "-started_at"], name="learn_attempt_user_started"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["open", "completed", "abandoned"]),
                name="learn_attempt_status",
            ),
            models.CheckConstraint(
                condition=Q(score__isnull=True) | Q(score__lte=100),
                name="learn_attempt_score",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.status} {self.challenge_id}"


class WorkspaceSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        ChallengeAttempt,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    schema_version = models.PositiveIntegerField(default=1)
    blockly_json = models.JSONField(default=dict)
    ast_dump = models.TextField(blank=True)
    pseudocode = models.TextField(blank=True)
    bindings = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"foto {self.schema_version}"


class HintUsage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        ChallengeAttempt,
        on_delete=models.CASCADE,
        related_name="hint_usages",
    )
    hint = models.ForeignKey(
        "learning.Hint",
        on_delete=models.PROTECT,
        related_name="usages",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.hint_id)


class Prediction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(
        ChallengeAttempt,
        on_delete=models.CASCADE,
        related_name="predictions",
    )
    prompt_key = models.CharField(max_length=80)
    expected = models.TextField()
    answer = models.TextField()
    is_correct = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.prompt_key


class Reflection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.OneToOneField(
        ChallengeAttempt,
        on_delete=models.CASCADE,
        related_name="reflection",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.body[:40]
