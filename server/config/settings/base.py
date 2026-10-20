"""Ajustes comunes. Los secretos entran por el entorno."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BASE_DIR.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = False
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "apps.accounts",
    "apps.billing",
    "apps.editor",
    "apps.language",
    "apps.projects",
    "apps.executions",
    "apps.flowcharts",
    "apps.audit",
    "apps.classroom",
    "apps.learning",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "config.middleware.ApiCsrfMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.IdleSessionMiddleware",
    "apps.billing.middleware.PlanGateMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.ContentSecurityPolicyMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "traza"),
        "USER": os.environ.get("POSTGRES_USER", "traza"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "traza"),
        "HOST": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("POSTGRES_PORT", "5433"),
    }
}

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "traza@localhost")
EMAIL_TIMEOUT = 10
TRAZA_PUBLIC_ORIGIN = os.environ.get("TRAZA_PUBLIC_ORIGIN", "http://127.0.0.1:18080").rstrip("/")
TRAZA_MAIL_UI = os.environ.get("TRAZA_MAIL_UI", "").rstrip("/")
EMAIL_CONFIRMATION_REQUIRED = os.environ.get("TRAZA_EMAIL_CONFIRMATION", "") == "1"

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_IDLE_SECONDS = 30 * 60
LOGIN_FAILURE_LIMIT = 3
LOGIN_LOCK_SECONDS = 15 * 60
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "traza",
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.TrazaPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "config.exceptions.traza_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Traza",
    "VERSION": "0.2.0",
}

REDIS_URL = os.environ.get("REDIS_URL", "")
EXECUTION_RUNNER = "inprocess"
# El alta real asigna el nivel gratis. Las pruebas usan premium para el comportamiento anterior.
TRAZA_SIGNUP_PLAN = "gratis"
MAX_SOURCE_BYTES = 64 * 1024
MAX_PROJECTS_PER_USER = 50
MAX_ALGORITHMS_PER_PROJECT = 200
MAX_COMMUNITIES_PER_TEACHER = 30
MAX_MEMBERS_PER_COMMUNITY = 200
MAX_FOLDER_DEPTH = 8
RATE_LIMITS = {
    "execution.start": (30, 60),
}
