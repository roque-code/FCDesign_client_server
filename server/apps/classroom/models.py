"""Comunidades de un docente. Las actividades y las entregas siguen fuera."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Community(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communities",
    )
    name = models.CharField(max_length=80)
    join_code = models.CharField(max_length=8, unique=True)
    translation_enabled = models.BooleanField(default=True)
    paste_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="uniq_community_name"),
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["community", "user"], name="uniq_community_member"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} en {self.community_id}"
