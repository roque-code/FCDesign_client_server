from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.services import consume_execution
from apps.http import current_user, object_body
from apps.languages.bridge import dispatch
from apps.languages.services import (
    create_program,
    get_program,
    list_programs,
    program_payload,
    student_programs,
    update_program,
)


class ProgramListView(APIView):
    def get(self, request: Request) -> Response:
        return Response({"results": list_programs(current_user(request))})

    def post(self, request: Request) -> Response:
        program = create_program(current_user(request), object_body(request.data))
        return Response(program_payload(program), status=201)


class ProgramDetailView(APIView):
    def get(self, request: Request, program_id) -> Response:
        return Response(program_payload(get_program(current_user(request), program_id)))

    def patch(self, request: Request, program_id) -> Response:
        program = get_program(current_user(request), program_id)
        return Response(program_payload(update_program(program, object_body(request.data))))

    def delete(self, request: Request, program_id) -> Response:
        get_program(current_user(request), program_id).delete()
        return Response(status=204)


class StudentProgramsView(APIView):
    def get(self, request: Request, user_id: int) -> Response:
        return Response(student_programs(current_user(request), user_id))


class LanguageStatusView(APIView):
    def post(self, request: Request) -> Response:
        return Response(dispatch("status", object_body(request.data)))


class LanguageRunView(APIView):
    def post(self, request: Request) -> Response:
        consume_execution(current_user(request))
        return Response(dispatch("run", object_body(request.data)))


class LanguageOpenView(APIView):
    def post(self, request: Request) -> Response:
        consume_execution(current_user(request))
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
