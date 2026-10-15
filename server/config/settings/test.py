"""Pruebas contra PostgreSQL, con correo en memoria."""

from config.settings.base import *  # noqa: F403

DEBUG = True
EXECUTION_RUNNER = "inprocess"
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
EMAIL_CONFIRMATION_REQUIRED = False
TRAZA_MAIL_UI = ""
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
RATE_LIMITS = {
    "auth.login": (3, 60),
    "execution.start": (3, 60),
}
