"""Producción no arranca con el intérprete dentro del proceso web.

El compose actual no usa este módulo. Cuando haya un servidor, el proceso
web debe apuntar aquí, con TRAZA_RUNNER=redis, REDIS_URL y EMAIL_HOST.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403

DEBUG = False
EXECUTION_RUNNER = os.environ.get("TRAZA_RUNNER", "inprocess")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

if EXECUTION_RUNNER != "redis":
    raise ImproperlyConfigured("El ejecutor en proceso no está disponible cuando DEBUG es falso.")
if not os.environ.get("REDIS_URL"):
    raise ImproperlyConfigured("La configuración de producción exige REDIS_URL.")
if not os.environ.get("EMAIL_HOST"):
    raise ImproperlyConfigured("La configuración de producción exige EMAIL_HOST.")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "") == "1"
