"""Comunidades de un docente. Las actividades y las entregas siguen fuera."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Community(models.Model):
    SUBJECTS = ("fundamentos", "bases", "objetos", "software")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communities",
    )
    subject = models.CharField(max_length=32)
    name = models.CharField(max_length=80)
    join_code = models.CharField(max_length=8, unique=True)
    translation_enabled = models.BooleanField(default=True)
    paste_enabled = models.BooleanField(default=True)
    # Vigilancia de foco en exámenes y retos. Sin límite no hay entrega automática.
    focus_watch = models.BooleanField(default=False)
    focus_limit = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "subject", "name"], name="uniq_community_owner_subject_name"),
            models.CheckConstraint(
                condition=Q(focus_limit__isnull=True)
                | Q(focus_limit__gte=1, focus_limit__lte=10),
                name="community_focus_limit",
            ),
            models.CheckConstraint(
                condition=Q(subject__in=["fundamentos", "bases", "objetos", "software"]),
                name="community_subject_known",
            ),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    community = models.ForeignKey(Community, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    # None hereda el grupo. True o False es la decisión para este alumno.
    translation_enabled = models.BooleanField(null=True, default=None)
    paste_enabled = models.BooleanField(null=True, default=None)
    focus_watch = models.BooleanField(null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["community", "user"], name="uniq_community_member"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} en {self.community_id}"


class ExerciseFeedback(models.Model):
    """Calificación y comentario de un docente sobre un ejercicio de su alumno."""

    ALGORITHM = "algorithm"
    PROGRAM = "program"
    KINDS = (ALGORITHM, PROGRAM)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feedback_given",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="feedback_received",
    )
    algorithm = models.ForeignKey(
        "projects.Algorithm",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    program = models.ForeignKey(
        "languages.LanguageProgram",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    grade = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(Q(algorithm__isnull=False) & Q(program__isnull=True))
                | (Q(algorithm__isnull=True) & Q(program__isnull=False)),
                name="feedback_one_exercise",
            ),
            models.CheckConstraint(
                condition=Q(grade__isnull=True) | (Q(grade__gte=0) & Q(grade__lte=100)),
                name="feedback_grade_range",
            ),
            models.UniqueConstraint(
                fields=["teacher", "algorithm"],
                condition=Q(algorithm__isnull=False),
                name="uniq_feedback_teacher_algorithm",
            ),
            models.UniqueConstraint(
                fields=["teacher", "program"],
                condition=Q(program__isnull=False),
                name="uniq_feedback_teacher_program",
            ),
        ]
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.teacher_id} → {self.student_id}"


class ExerciseFocus(models.Model):
    """Salidas de la plataforma mientras el alumno trabaja un ejercicio del editor."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exercise_focus",
    )
    algorithm = models.OneToOneField(
        "projects.Algorithm",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="focus_log",
    )
    program = models.OneToOneField(
        "languages.LanguageProgram",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="focus_log",
    )
    focus = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(Q(algorithm__isnull=False) & Q(program__isnull=True))
                | (Q(algorithm__isnull=True) & Q(program__isnull=False)),
                name="exercise_focus_one_exercise",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student_id} foco"
