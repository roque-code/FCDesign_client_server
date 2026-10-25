"""Usuario identificado por correo. La primera migración ya usa este modelo."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> User:
        if not email:
            raise ValueError("El correo es obligatorio.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superusuario debe tener is_staff e is_superuser.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None  # type: ignore[assignment]
    email = models.EmailField("correo", unique=True)
    email_confirmed = models.BooleanField("correo confirmado", default=True)
    session_key = models.CharField("sesión activa", max_length=40, blank=True, default="")
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()  # type: ignore[misc,assignment]

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="uniq_user_email_ci"),
        ]

    def __str__(self) -> str:
        return self.email


class Profile(models.Model):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=80)
    institution = models.CharField(max_length=120, blank=True)
    role = models.CharField(max_length=16, default=STUDENT)
    points = models.PositiveIntegerField(default=0)
    avatar = models.BinaryField(null=True, blank=True)
    avatar_type = models.CharField(max_length=16, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name


class SignupPolicy(models.Model):
    """Una sola fila. El administrador elige qué altas aparecen."""

    student = models.BooleanField("alta de alumno", default=True)
    teacher = models.BooleanField("alta de docente", default=True)

    class Meta:
        verbose_name = "altas"
        verbose_name_plural = "altas"
