"""Niveles de suscripción. El precio y las funciones viven en estas filas."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Plan(models.Model):
    STUDENT = "student"
    TEACHER = "teacher"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=32)
    name = models.CharField(max_length=80)
    audience = models.CharField(max_length=16)
    price_cents = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="MXN")
    period_days = models.PositiveIntegerField(default=0)
    browser_allowed = models.BooleanField(default=False)
    max_projects = models.PositiveIntegerField(null=True, blank=True)
    max_algorithms = models.PositiveIntegerField(null=True, blank=True)
    features = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["audience", "sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["audience", "code"], name="uniq_plan_code"),
            models.UniqueConstraint(
                fields=["audience"],
                condition=Q(is_default=True),
                name="uniq_default_plan",
            ),
            models.CheckConstraint(
                condition=Q(audience__in=["student", "teacher"]),
                name="plan_audience",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.audience})"


class Subscription(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    paid_until = models.DateTimeField(null=True, blank=True)
    browser_allowed = models.BooleanField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user_id} → {self.plan_id}"
