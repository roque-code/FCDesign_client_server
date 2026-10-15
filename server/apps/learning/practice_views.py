from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.http import current_user, object_body
from apps.learning.practices import (
    create_practice,
    delete_practice,
    get_practice,
    list_practices,
    update_practice,
)


class PracticeListView(APIView):
    def get(self, request: Request) -> Response:
        return Response(list_practices(current_user(request)))

    def post(self, request: Request) -> Response:
        return Response(
            create_practice(current_user(request), object_body(request.data)), status=201
        )


class PracticeDetailView(APIView):
    def get(self, request: Request, practice_id) -> Response:
        return Response(get_practice(current_user(request), practice_id))

    def patch(self, request: Request, practice_id) -> Response:
        return Response(
            update_practice(current_user(request), practice_id, object_body(request.data))
        )

    def delete(self, request: Request, practice_id) -> Response:
        delete_practice(current_user(request), practice_id)
        return Response(status=204)
