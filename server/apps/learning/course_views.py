from django.http import HttpResponse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.http import current_user, object_body
from apps.learning.gradebook import gradebook_csv
from apps.learning.progress import (
    challenge_payload,
    check_attempt,
    close_attempt,
    expire_attempt,
    path_payload,
    paths_payload,
    reveal_hint,
    run_prediction,
    save_stage,
    start_attempt,
    submit_language,
)
from apps.learning.roster import member_progress, member_work, roster_payload


class RosterView(APIView):
    def get(self, request: Request) -> Response:
        return Response(roster_payload(current_user(request)))


class RosterProgressView(APIView):
    def get(self, request: Request, path_id) -> HttpResponse:
        lang = request.query_params.get("lang", "es")
        filename, body = gradebook_csv(current_user(request), path_id, str(lang))
        response = HttpResponse(body, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class MemberProgressView(APIView):
    def get(self, request: Request, user_id: int) -> Response:
        return Response(member_progress(current_user(request), user_id))


class MemberWorkView(APIView):
    def get(self, request: Request, user_id: int, challenge_id) -> Response:
        return Response(member_work(current_user(request), user_id, challenge_id))


class PathView(APIView):
    def get(self, request: Request) -> Response:
        return Response(path_payload(current_user(request)))


class PathsView(APIView):
    def get(self, request: Request) -> Response:
        return Response(paths_payload(current_user(request)))


class ChallengeDetailView(APIView):
    def get(self, request: Request, challenge_id) -> Response:
        return Response(challenge_payload(current_user(request), challenge_id))


class AttemptStartView(APIView):
    def post(self, request: Request, challenge_id) -> Response:
        data = object_body(request.data)
        return Response(start_attempt(current_user(request), challenge_id, data.get("path_id")))


class AttemptStageView(APIView):
    def post(self, request: Request, attempt_id) -> Response:
        data = object_body(request.data)
        return Response(
            save_stage(current_user(request), attempt_id, data.get("stage"), data.get("answer"))
        )


class AttemptHintView(APIView):
    def post(self, request: Request, attempt_id) -> Response:
        return Response(reveal_hint(current_user(request), attempt_id))


class AttemptCheckView(APIView):
    def post(self, request: Request, attempt_id) -> Response:
        return Response(check_attempt(current_user(request), attempt_id, object_body(request.data)))


class AttemptRunView(APIView):
    def post(self, request: Request, attempt_id) -> Response:
        return Response(run_prediction(current_user(request), attempt_id))


class AttemptExpireView(APIView):
    def post(self, request: Request, attempt_id) -> Response:
        return Response(expire_attempt(current_user(request), attempt_id))


class AttemptLanguageView(APIView):
    def post(self, request: Request, attempt_id) -> Response:
        return Response(
            submit_language(current_user(request), attempt_id, object_body(request.data))
        )


class AttemptCloseView(APIView):
    def post(self, request: Request, attempt_id) -> Response:
        data = object_body(request.data)
        return Response(close_attempt(current_user(request), attempt_id, data.get("reflection")))
