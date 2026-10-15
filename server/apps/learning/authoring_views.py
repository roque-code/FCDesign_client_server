from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.http import current_user, object_body
from apps.learning.authoring import (
    bank_payload,
    catalog_payload,
    create_challenge,
    create_path,
    delete_challenge,
    delete_path,
    list_paths,
    path_detail,
    read_challenge,
    set_assignments,
    set_challenges,
    update_challenge,
    update_entry,
    update_path,
)


class CatalogView(APIView):
    def get(self, request: Request) -> Response:
        return Response(catalog_payload(current_user(request)))


class BankView(APIView):
    def get(self, request: Request) -> Response:
        return Response(bank_payload(current_user(request)))


class AuthoredListView(APIView):
    def get(self, request: Request) -> Response:
        return Response(list_paths(current_user(request)))

    def post(self, request: Request) -> Response:
        return Response(create_path(current_user(request), object_body(request.data)), status=201)


class AuthoredDetailView(APIView):
    def get(self, request: Request, path_id) -> Response:
        return Response(path_detail(current_user(request), path_id))

    def patch(self, request: Request, path_id) -> Response:
        return Response(update_path(current_user(request), path_id, object_body(request.data)))

    def delete(self, request: Request, path_id) -> Response:
        delete_path(current_user(request), path_id)
        return Response(status=204)


class AuthoredChallengeCollectionView(APIView):
    def post(self, request: Request) -> Response:
        return Response(
            create_challenge(current_user(request), object_body(request.data)),
            status=201,
        )


class AuthoredChallengeEditorView(APIView):
    def get(self, request: Request, challenge_id) -> Response:
        return Response(read_challenge(current_user(request), challenge_id))

    def patch(self, request: Request, challenge_id) -> Response:
        return Response(
            update_challenge(current_user(request), challenge_id, object_body(request.data))
        )

    def delete(self, request: Request, challenge_id) -> Response:
        delete_challenge(current_user(request), challenge_id)
        return Response(status=204)


class AuthoredChallengesView(APIView):
    def put(self, request: Request, path_id) -> Response:
        data = object_body(request.data)
        return Response(set_challenges(current_user(request), path_id, data.get("challenge_ids")))


class AuthoredEntryView(APIView):
    def patch(self, request: Request, path_id, challenge_id) -> Response:
        return Response(
            update_entry(
                current_user(request),
                path_id,
                challenge_id,
                object_body(request.data),
            )
        )


class AuthoredAssignmentsView(APIView):
    def put(self, request: Request, path_id) -> Response:
        data = object_body(request.data)
        return Response(
            set_assignments(
                current_user(request),
                path_id,
                data.get("community_ids"),
                data.get("student_ids"),
            )
        )
