from django.conf import settings
from django.db import models


class EditorPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="editor_preference",
    )
    theme = models.CharField(max_length=16, default="light")
    font_size = models.PositiveSmallIntegerField(default=16)
    keymap = models.CharField(max_length=32, default="default")
    indent_size = models.PositiveSmallIntegerField(default=4)
    autosave = models.BooleanField(default=True)
    locale = models.CharField(max_length=8, default="es")
    require_semicolons = models.BooleanField(default=True)
    index_base = models.PositiveSmallIntegerField(default=1)

    def __str__(self) -> str:
        return f"{self.user_id}:{self.theme}"
