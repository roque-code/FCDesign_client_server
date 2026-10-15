"""Estado del proceso web y del runner, sin secretos de producción."""

from django.conf import settings
from django.db import connections
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        checks: dict[str, bool] = {}
        try:
            connections["default"].ensure_connection()
            checks["database"] = True
        except Exception:
            checks["database"] = False
        if settings.EXECUTION_RUNNER == "redis":
            from apps.executions.bus import heartbeat_ok

            checks["runner"] = heartbeat_ok()
        ready = all(checks.values())
        return Response(
            {"status": "ok" if ready else "degraded", "checks": checks},
            status=200 if ready else 503,
        )
