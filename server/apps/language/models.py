from django.db import models

from config.errors import DomainError


class LanguageProfile(models.Model):
    key = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=80)
    config = models.JSONField(default=dict)
    is_system = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.key

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise DomainError("No se puede borrar un perfil de fábrica.", code="protected")
        return super().delete(*args, **kwargs)
