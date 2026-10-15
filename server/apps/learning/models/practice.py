"""Prácticas libres guardadas. No son algoritmos del banco de trabajo."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Practice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="learning_practices",
    )
    name = models.CharField(max_length=120)
    workspace = models.JSONField(default=dict)
    source = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="uniq_practice_user_name"),
        ]
        indexes = [
            models.Index(fields=["user", "-updated_at"], name="learn_practice_user_updated"),
        ]

    def __str__(self) -> str:
        return self.name
