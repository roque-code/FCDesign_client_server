from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.executions.live import peek, stream
from apps.executions.services import (
    breakpoint_set,
    control_execution,
    execution_payload,
    get_execution,
    inspect_array,
    start_debug,
    start_execution,
    submit_input,
)
from apps.http import client_ip, object_body
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


class ExecuteView(APIView):
    def post(self, request: Request, algorithm_id) -> Response:
        execution, diagnostics = start_execution(request.user, algorithm_id, client_ip(request))
        return Response(execution_payload(execution, diagnostics), status=201)


class DebugView(APIView):
    def post(self, request: Request, algorithm_id) -> Response:
        data = object_body(request.data)
        execution, diagnostics = start_debug(
            request.user,
            algorithm_id,
            breakpoint_set(data.get("breakpoints")),
            client_ip(request),
        )
        return Response(execution_payload(execution, diagnostics), status=201)


class ExecutionDetailView(APIView):
    def get(self, request: Request, execution_id) -> Response:
        return Response(execution_payload(get_execution(request.user, execution_id)))


class ExecutionInputView(APIView):
    def post(self, request: Request, execution_id) -> Response:
        data = object_body(request.data)
        execution, diagnostics = submit_input(request.user, execution_id, data.get("text"))
        return Response(execution_payload(execution, diagnostics))


class ExecutionControlView(APIView):
    def post(self, request: Request, execution_id) -> Response:
        data = object_body(request.data)
        marks = breakpoint_set(data.get("breakpoints")) if "breakpoints" in data else None
        execution, diagnostics = control_execution(
            request.user, execution_id, data.get("action"), marks
        )
        return Response(execution_payload(execution, diagnostics))


class ExecutionInspectView(APIView):
    def post(self, request: Request, execution_id) -> Response:
        data = object_body(request.data)
        return Response(
            inspect_array(
                request.user,
                execution_id,
                data.get("name"),
                data.get("start", 0),
                data.get("count", 20),
            )
        )


class ExecutionEventsView(APIView):
    renderer_classes = [EventStreamRenderer, JSONRenderer]

    def get(self, request: Request, execution_id) -> StreamingHttpResponse:
        execution = get_execution(request.user, execution_id)
        header = request.headers.get("Last-Event-ID", "0")
        try:
            after = int(header)
        except ValueError:
            after = 0
        once = request.query_params.get("once") == "1"
        if settings.EXECUTION_RUNNER == "redis":
            from apps.executions.bus import fetch_state, iter_events

            if fetch_state(str(execution.id)) is None:
                raise DomainError(
                    "La sesión de depuración ya no está en memoria. Vuelve a depurar.",
                    code="conflict",
                    status_code=409,
                )
            frames = iter_events(str(execution.id), after, once=once)
        else:
            live = peek(str(execution.id))
            if live is None:
                raise DomainError(
                    "La sesión de depuración ya no está en memoria. Vuelve a depurar.",
                    code="conflict",
                    status_code=409,
                )
            frames = stream(live, str(execution.id), after, once=once)
        response = StreamingHttpResponse(
            frames,
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response
