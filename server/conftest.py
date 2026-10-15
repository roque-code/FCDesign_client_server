import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.tests.helpers import refresh_csrf


@pytest.fixture(autouse=True)
def _clear_rate_limit():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def client(db):
    api = APIClient(enforce_csrf_checks=True)
    refresh_csrf(api)
    return api
