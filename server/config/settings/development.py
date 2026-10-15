"""Desarrollo: en la máquina, el intérprete corre en este proceso.

El compose de contenedores define TRAZA_RUNNER=redis. Sigue siendo
desarrollo: DEBUG queda en verdadero y no se carga la configuración
de producción.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403

DEBUG = True
EXECUTION_RUNNER = os.environ.get("TRAZA_RUNNER", "inprocess")
if EXECUTION_RUNNER not in ("inprocess", "redis"):
    raise ImproperlyConfigured("TRAZA_RUNNER debe ser inprocess o redis.")
if EXECUTION_RUNNER == "redis" and not os.environ.get("REDIS_URL"):
    raise ImproperlyConfigured("TRAZA_RUNNER=redis exige REDIS_URL.")
if os.environ.get("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.environ["REDIS_URL"],
        }
    }
if os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "1025"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "") == "1"
    EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "") == "1"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "DJANGO_CSRF_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173",
    ).split(",")
    if origin.strip()
]
