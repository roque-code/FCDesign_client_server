"""Producción: TLS lo termina Nginx y el ejecutor va por Redis.

El compose del servidor apunta aquí. Exige TRAZA_RUNNER=redis, REDIS_URL,
EMAIL_HOST, un origen https y una clave distinta de las de desarrollo.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403

DEBUG = False
EXECUTION_RUNNER = os.environ.get("TRAZA_RUNNER", "inprocess")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Una hora hasta comprobar el inicio de sesión por HTTPS. Subirlo antes
# dejaría el navegador atado a este nombre si el certificado falla.
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

_DEV_SECRETS = {"", "dev-only-change-me", "dev-container-not-production"}

if EXECUTION_RUNNER != "redis":
    raise ImproperlyConfigured("El ejecutor en proceso no está disponible cuando DEBUG es falso.")
if not os.environ.get("REDIS_URL"):
    raise ImproperlyConfigured("La configuración de producción exige REDIS_URL.")
if not os.environ.get("EMAIL_HOST"):
    raise ImproperlyConfigured("La configuración de producción exige EMAIL_HOST.")
if os.environ.get("DJANGO_SECRET_KEY", "") in _DEV_SECRETS:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY de producción no puede ser la de desarrollo.")

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_ORIGINS", "").split(",")
    if origin.strip()
]
if not CSRF_TRUSTED_ORIGINS or any(
    not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured("DJANGO_CSRF_ORIGINS en producción tiene que ser una lista https.")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ["REDIS_URL"],
    }
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ["EMAIL_HOST"]
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "") == "1"
