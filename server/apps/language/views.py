from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from language_core.grammar import KEYWORD_DISPLAY, STDLIB_DISPLAY


class KeywordView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response({"keywords": list(KEYWORD_DISPLAY), "stdlib": list(STDLIB_DISPLAY)})


class MetaView(APIView):
    def get(self, request: Request) -> Response:
        notice = None
        if settings.DEBUG and settings.EXECUTION_RUNNER == "inprocess":
            notice = (
                "La ejecución ocurre en el proceso de desarrollo, con límites lógicos. "
                "No es el aislamiento de producción."
            )
        return Response(
            {
                "product": "Traza",
                "runner": settings.EXECUTION_RUNNER,
                "debug": settings.DEBUG,
                "notice": notice,
            }
        )
