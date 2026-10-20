import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

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


@pytest.fixture
def client(db):
    api = APIClient(enforce_csrf_checks=True)
    refresh_csrf(api)
    return api
