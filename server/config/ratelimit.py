"""Límite de peticiones sobre la caché. En desarrollo la caché es local."""

from django.conf import settings
from django.core.cache import cache

from config.errors import DomainError


def allow(bucket: str, identity: str) -> None:
    limit, window = settings.RATE_LIMITS[bucket]
    key = f"rl:{bucket}:{identity}"
    if cache.add(key, 1, timeout=window):
        return
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)
        return
    if int(count) > limit:
        raise DomainError(
            "Demasiadas solicitudes. Espera un momento.",
            code="rate_limited",
            status_code=429,
        )
