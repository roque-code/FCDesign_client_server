"""Vistas del examen. La regla vive en services."""

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.exams.services import (
    attempt_view,
    close_exam,
    create_exam,
    delete_exam,
    exam_detail,
    export_exam,
    focus_attempt,
    get_exam,
    grade_manual,
    grades_csv,
    import_exam,
    list_exams,
    list_mine,
    list_notices,
    mark_notices,
    open_attempt,
    publish_exam,
    results,
    save_attempt,
    start_attempt,
    submit_attempt,
    update_exam,
)
from apps.http import client_ip, current_user, object_body


class ExamListView(APIView):
    def get(self, request: Request) -> Response:
        return Response(
            {"results": list_exams(current_user(request), request.query_params.get("subject"))}
        )

    def post(self, request: Request) -> Response:
        exam = create_exam(current_user(request), object_body(request.data), client_ip(request))
        return Response(exam_detail(exam), status=201)


class ExamMineView(APIView):
    def get(self, request: Request) -> Response:
        return Response({"results": list_mine(current_user(request))})


class ExamNoticeView(APIView):
    def get(self, request: Request) -> Response:
        return Response(list_notices(current_user(request)))

    def post(self, request: Request) -> Response:
        return Response(mark_notices(current_user(request)))


class ExamImportView(APIView):
    def post(self, request: Request) -> Response:
        exam = import_exam(current_user(request), object_body(request.data), client_ip(request))
        return Response(exam_detail(exam), status=201)


class ExamDetailView(APIView):
    def get(self, request: Request, exam_id) -> Response:
        return Response(exam_detail(get_exam(current_user(request), exam_id)))

    def patch(self, request: Request, exam_id) -> Response:
        exam = update_exam(
            current_user(request), exam_id, object_body(request.data), client_ip(request)
        )
        return Response(exam_detail(exam))

    def delete(self, request: Request, exam_id) -> Response:
        delete_exam(current_user(request), exam_id, client_ip(request))
        return Response(status=204)


class ExamPublishView(APIView):
    def post(self, request: Request, exam_id) -> Response:
        return Response(publish_exam(current_user(request), exam_id, client_ip(request)))


class ExamCloseView(APIView):
    def post(self, request: Request, exam_id) -> Response:
        return Response(exam_detail(close_exam(current_user(request), exam_id, client_ip(request))))


class ExamExportView(APIView):
    def get(self, request: Request, exam_id) -> Response:
        # DRF reserva ?format= para elegir el renderizador: con moodle o gift responde 404.
        fmt = request.query_params.get("as") or request.query_params.get("format")
        return Response(export_exam(current_user(request), exam_id, fmt))


class ExamResultsView(APIView):
    def get(self, request: Request, exam_id) -> Response:
        return Response(results(current_user(request), exam_id))


class ExamGradesView(APIView):
    def get(self, request: Request, exam_id) -> Response:
        return Response(grades_csv(current_user(request), exam_id))


class ExamStartView(APIView):
    def post(self, request: Request, exam_id) -> Response:
        attempt = start_attempt(current_user(request), exam_id, client_ip(request))
        return Response(attempt_view(attempt, teacher=False), status=201)


class ExamAttemptView(APIView):
    def get(self, request: Request, attempt_id) -> Response:
        return Response(open_attempt(current_user(request), attempt_id))

    def patch(self, request: Request, attempt_id) -> Response:
        attempt = save_attempt(
            current_user(request), attempt_id, object_body(request.data), client_ip(request)
        )
        return Response(attempt_view(attempt, teacher=False))


class ExamSubmitView(APIView):
    def post(self, request: Request, attempt_id) -> Response:
        attempt = submit_attempt(
            current_user(request), attempt_id, object_body(request.data), client_ip(request)
        )
        return Response(attempt_view(attempt, teacher=False))


class ExamFocusView(APIView):
    def post(self, request: Request, attempt_id) -> Response:
        attempt = focus_attempt(
            current_user(request), attempt_id, object_body(request.data), client_ip(request)
        )
        return Response(attempt_view(attempt, teacher=False))


class ExamGradeView(APIView):
    def post(self, request: Request, attempt_id) -> Response:
        attempt = grade_manual(
            current_user(request), attempt_id, object_body(request.data), client_ip(request)
        )
        return Response(attempt_view(attempt, teacher=True))
