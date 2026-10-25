from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.http import object_body
from apps.languages.bridge import dispatch


class LanguageStatusView(APIView):
    def post(self, request: Request) -> Response:
        return Response(dispatch("status", object_body(request.data)))


class LanguageRunView(APIView):
    def post(self, request: Request) -> Response:
        return Response(dispatch("run", object_body(request.data)))


class LanguageOpenView(APIView):
    def post(self, request: Request) -> Response:
        return Response(dispatch("open", object_body(request.data)))


class LanguageInputView(APIView):
    def post(self, request: Request) -> Response:
        return Response(dispatch("input", object_body(request.data)))


class LanguagePollView(APIView):
    def post(self, request: Request) -> Response:
        return Response(dispatch("poll", object_body(request.data)))


class LanguageCloseView(APIView):
    def post(self, request: Request) -> Response:
        return Response(dispatch("close", object_body(request.data)))
