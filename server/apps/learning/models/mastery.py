"""Conceptos y dominio por alumno."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class Concept(models.Model):
    """Clave natural. El catálogo crece con migraciones de datos, no con otra tabla."""

    key = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return self.name


class ConceptMastery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="concept_masteries",
    )
    concept = models.ForeignKey(Concept, on_delete=models.PROTECT, related_name="masteries")
    level = models.PositiveSmallIntegerField(default=0)
    evidence = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "concept"], name="uniq_concept_mastery"),
            models.CheckConstraint(
                condition=Q(level__gte=0, level__lte=5),
                name="concept_mastery_level",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.concept_id} {self.level}"
