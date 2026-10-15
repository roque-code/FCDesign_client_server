from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.executions.live import stream
from apps.http import current_user, object_body
from apps.learning.imports import import_source
from apps.learning.runs import control_run, read_run, require_run, start_run, submit_run_input
from apps.learning.services import preview_workspace
from config.errors import DomainError


class EventStreamRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "txt"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None) -> bytes:
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode("utf-8")
        return b""


class PreviewView(APIView):
    def post(self, request: Request) -> Response:
        current_user(request)
        return Response(preview_workspace(object_body(request.data)))


class ImportView(APIView):
    def post(self, request: Request) -> Response:
        current_user(request)
        return Response(import_source(object_body(request.data)))


class RunStartView(APIView):
    def post(self, request: Request) -> Response:
        user = current_user(request)
        return Response(start_run(user, object_body(request.data)))


class RunControlView(APIView):
    def post(self, request: Request, run_id) -> Response:
        user = current_user(request)
        data = object_body(request.data)
        return Response(control_run(user, str(run_id), data.get("action")))


class RunInputView(APIView):
    def post(self, request: Request, run_id) -> Response:
        user = current_user(request)
        data = object_body(request.data)
        return Response(submit_run_input(user, str(run_id), data.get("text")))


class RunDetailView(APIView):
    def get(self, request: Request, run_id) -> Response:
        return Response(read_run(current_user(request), str(run_id)))


class RunEventsView(APIView):
    renderer_classes = [EventStreamRenderer, JSONRenderer]

    def get(self, request: Request, run_id) -> StreamingHttpResponse:
        user = current_user(request)
        header = request.headers.get("Last-Event-ID", "0")
        try:
            after = int(header)
        except ValueError:
            after = 0
        once = request.query_params.get("once") == "1"
        if settings.EXECUTION_RUNNER == "redis":
            from apps.executions.bus import iter_events, load_meta

            meta = load_meta(str(run_id))
            owner = None if meta is None else meta.get("user_id")
            if meta is None or owner != user.pk or meta.get("kind") != "lab":
                raise DomainError(
                    "No se encontró esta pasada del laboratorio.",
                    code="not_found",
                    status_code=404,
                )
            frames = iter_events(str(run_id), after, once=once)
        else:
            live = require_run(user, str(run_id))
            frames = stream(live, str(run_id), after, once=once)
        response = StreamingHttpResponse(
            frames,
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
