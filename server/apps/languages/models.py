import uuid

from django.conf import settings
from django.db import models

LANGUAGES = ("python", "javascript", "typescript", "java", "c", "cpp", "csharp")


class LanguageProgram(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="language_programs",
    )
    name = models.CharField(max_length=120)
    language = models.CharField(max_length=16)
    source = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "language", "name"],
                name="uniq_language_program_name",
            ),
            models.CheckConstraint(
                condition=models.Q(language__in=LANGUAGES),
                name="language_program_language",
            ),
        ]
        indexes = [models.Index(fields=["owner", "updated_at"])]
