import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.billing.models import Plan
from apps.tests.helpers import refresh_csrf


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def _desktop_client(monkeypatch):
    """La suite habla como la aplicación. El navegador se prueba sin esta cabecera."""
    original = APIClient.__init__

    def patched(self, enforce_csrf_checks=False, **defaults):
        defaults.setdefault("HTTP_X_AULIVANA_FCDDESIGN_CLIENT", "desktop")
        original(self, enforce_csrf_checks=enforce_csrf_checks, **defaults)

    monkeypatch.setattr(APIClient, "__init__", patched)


@pytest.fixture(autouse=True)
def _paid_plans_keep_unlimited_runs(db):
    """La suite de ejecución usa premium. El tope diario se prueba a propósito."""
    Plan.objects.filter(is_default=False).update(max_executions_per_day=None)


@pytest.fixture
def client(db):
    api = APIClient(enforce_csrf_checks=True)
    refresh_csrf(api)
    return api
