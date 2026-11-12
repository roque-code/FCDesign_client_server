"""Examen programado para una materia y un grupo."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Exam(models.Model):
    SUBJECTS = ("fundamentos", "bases", "objetos", "software")
    ALL = "all"
    SELECTED = "selected"
    AUDIENCES = (ALL, SELECTED)
    HIGHEST = "highest"
    AVERAGE = "average"
    FIRST = "first"
    LAST = "last"
    METHODS = (HIGHEST, AVERAGE, FIRST, LAST)
    FREE = "free"
    SEQUENTIAL = "sequential"
    NAVIGATIONS = (FREE, SEQUENTIAL)
    IMMEDIATE = "immediate"
    AFTER_CLOSE = "after_close"
    REVEALS = (IMMEDIATE, AFTER_CLOSE)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exams",
    )
    community = models.ForeignKey(
        "classroom.Community",
        on_delete=models.CASCADE,
        related_name="exams",
    )
    subject = models.CharField(max_length=32)
    title = models.CharField(max_length=140)
    instructions = models.TextField(blank=True)
    opens_at = models.DateTimeField(null=True, blank=True)
    closes_at = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    attempts_allowed = models.PositiveSmallIntegerField(default=1)
    grading_method = models.CharField(max_length=16, default=HIGHEST)
    shuffle_questions = models.BooleanField(default=False)
    shuffle_choices = models.BooleanField(default=True)
    navigation = models.CharField(max_length=16, default=FREE)
    one_per_page = models.BooleanField(default=False)
    grade_to_pass = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    show_grade = models.CharField(max_length=16, default=IMMEDIATE)
    audience = models.CharField(max_length=16, default=ALL)
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(subject__in=["fundamentos", "bases", "objetos", "software"]),
                name="exam_subject_known",
            ),
            models.CheckConstraint(
                condition=Q(audience__in=["all", "selected"]),
                name="exam_audience_known",
            ),
            models.CheckConstraint(
                condition=Q(grading_method__in=["highest", "average", "first", "last"]),
                name="exam_grading_method",
            ),
            models.CheckConstraint(
                condition=Q(navigation__in=["free", "sequential"]),
                name="exam_navigation",
            ),
            models.CheckConstraint(
                condition=Q(show_grade__in=["immediate", "after_close"]),
                name="exam_show_grade",
            ),
            models.CheckConstraint(
                condition=Q(duration_minutes__isnull=True)
                | Q(duration_minutes__gte=1, duration_minutes__lte=480),
                name="exam_duration",
            ),
            models.CheckConstraint(
                condition=Q(attempts_allowed__gte=1, attempts_allowed__lte=20),
                name="exam_attempts",
            ),
            models.CheckConstraint(
                condition=Q(grade_to_pass__isnull=True)
                | Q(grade_to_pass__gte=0, grade_to_pass__lte=100),
                name="exam_grade_to_pass",
            ),
            models.CheckConstraint(
                condition=Q(opens_at__isnull=True)
                | Q(closes_at__isnull=True)
                | Q(opens_at__lt=models.F("closes_at")),
                name="exam_window_order",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class ExamSeat(models.Model):
    """Alumno elegido cuando el examen no es para todo el grupo."""

    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="seats")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_seats",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["exam", "user"], name="uniq_exam_seat"),
        ]


class ExamQuestion(models.Model):
    CHOICE = "choice"
    MULTI = "multi"
    TRUE_FALSE = "true_false"
    SHORT = "short"
    NUMERICAL = "numerical"
    ESSAY = "essay"
    MATCHING = "matching"
    ORDER = "order"
    CLOZE = "cloze"
    CASE = "case"
    KINDS = (CHOICE, MULTI, TRUE_FALSE, SHORT, NUMERICAL, ESSAY, MATCHING, ORDER, CLOZE, CASE)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")
    position = models.PositiveIntegerField()
    kind = models.CharField(max_length=16)
    prompt = models.TextField()
    points = models.DecimalField(max_digits=6, decimal_places=2)
    feedback = models.TextField(blank=True)
    payload = models.JSONField(default=dict)

    class Meta:
        ordering = ["exam", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "position"], name="uniq_exam_question_position"
            ),
            models.CheckConstraint(
                condition=Q(
                    kind__in=[
                        "choice",
                        "multi",
                        "true_false",
                        "short",
                        "numerical",
                        "essay",
                        "matching",
                        "order",
                        "cloze",
                        "case",
                    ]
                ),
                name="exam_question_kind",
            ),
            models.CheckConstraint(
                condition=Q(points__gt=0, points__lte=100),
                name="exam_question_points",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.position}. {self.kind}"


class ExamAttempt(models.Model):
    OPEN = "open"
    SUBMITTED = "submitted"
    GRADED = "graded"
    STATES = (OPEN, SUBMITTED, GRADED)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="attempts")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_attempts",
    )
    number = models.PositiveSmallIntegerField()
    state = models.CharField(max_length=16, default=OPEN)
    started_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    layout = models.JSONField(default=dict)
    score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    focus = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["exam", "student", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "student", "number"],
                name="uniq_exam_attempt_number",
            ),
            models.CheckConstraint(
                condition=Q(state__in=["open", "submitted", "graded"]),
                name="exam_attempt_state",
            ),
        ]


class ExamResponse(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE, related_name="responses")
    answer = models.JSONField(default=dict)
    score = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pending = models.BooleanField(default=False)
    comment = models.TextField(blank=True)
    detail = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="uniq_exam_response",
            ),
        ]


class ExamNotice(models.Model):
    ASSIGNED = "assigned"
    GRADED = "graded"
    KINDS = (ASSIGNED, GRADED)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="notices")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exam_notices",
    )
    attempt = models.ForeignKey(
        ExamAttempt,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notices",
    )
    kind = models.CharField(max_length=16)
    percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=["assigned", "graded"]),
                name="exam_notice_kind",
            ),
            models.UniqueConstraint(
                fields=["exam", "user", "kind"],
                condition=Q(attempt__isnull=True),
                name="uniq_exam_notice_assigned",
            ),
            models.UniqueConstraint(
                fields=["attempt", "kind"],
                condition=Q(attempt__isnull=False),
                name="uniq_exam_notice_attempt",
            ),
        ]
