from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.http import client_ip, current_user, object_body
from apps.language.services import diagnostic_payload, profile_for_algorithm
from apps.projects.services import (
    algorithm_payload,
    create_algorithm,
    create_folder,
    create_project,
    create_share,
    folder_payload,
    get_algorithm,
    get_folder,
    get_project,
    parse_expiry,
    project_payload,
    read_share,
    restore_project,
    restore_version,
    revoke_share,
    save_algorithm,
    soft_delete_algorithm,
    soft_delete_folder,
    soft_delete_project,
    update_algorithm,
    update_folder,
    update_project,
    version_payload,
)
from config.pagination import TrazaPagination
from language_core import compile_source


class ProjectListView(APIView):
    def get(self, request: Request) -> Response:
        queryset = current_user(request).projects.all().order_by("name")
        return _page(request, queryset, project_payload)

    def post(self, request: Request) -> Response:
        project = create_project(request.user, object_body(request.data), client_ip(request))
        return Response(project_payload(project), status=201)


class ProjectDetailView(APIView):
    def get(self, request: Request, project_id) -> Response:
        return Response(project_payload(get_project(request.user, project_id)))

    def patch(self, request: Request, project_id) -> Response:
        project = update_project(get_project(request.user, project_id), object_body(request.data))
        return Response(project_payload(project))

    def delete(self, request: Request, project_id) -> Response:
        soft_delete_project(get_project(request.user, project_id), request.user, client_ip(request))
        return Response(status=204)


class ProjectRestoreView(APIView):
    def post(self, request: Request, project_id) -> Response:
        return Response(project_payload(restore_project(request.user, project_id)))


class FolderListView(APIView):
    def get(self, request: Request, project_id) -> Response:
        project = get_project(request.user, project_id)
        folders = project.folders.all().order_by("name")
        return _page(request, folders, folder_payload)

    def post(self, request: Request, project_id) -> Response:
        project = get_project(request.user, project_id)
        folder = create_folder(project, object_body(request.data))
        return Response(folder_payload(folder), status=201)


class FolderDetailView(APIView):
    def patch(self, request: Request, folder_id) -> Response:
        folder = update_folder(get_folder(request.user, folder_id), object_body(request.data))
        return Response(folder_payload(folder))

    def delete(self, request: Request, folder_id) -> Response:
        soft_delete_folder(get_folder(request.user, folder_id))
        return Response(status=204)


class AlgorithmListView(APIView):
    def get(self, request: Request) -> Response:
        user = current_user(request)
        queryset = user.algorithms.select_related("language_profile").filter(
            project__deleted_at__isnull=True,
            project__owner=user,
        )
        project_id = request.query_params.get("project")
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return _page(request, queryset.order_by("name"), algorithm_payload)

    def post(self, request: Request) -> Response:
        algorithm = create_algorithm(request.user, object_body(request.data))
        return Response(algorithm_payload(algorithm), status=201)


class AlgorithmDetailView(APIView):
    def get(self, request: Request, algorithm_id) -> Response:
        return Response(algorithm_payload(get_algorithm(request.user, algorithm_id)))

    def patch(self, request: Request, algorithm_id) -> Response:
        algorithm = update_algorithm(
            get_algorithm(request.user, algorithm_id),
            object_body(request.data),
        )
        return Response(algorithm_payload(algorithm))

    def delete(self, request: Request, algorithm_id) -> Response:
        soft_delete_algorithm(
            get_algorithm(request.user, algorithm_id),
            request.user,
            client_ip(request),
        )
        return Response(status=204)


class AlgorithmSaveView(APIView):
    def post(self, request: Request, algorithm_id) -> Response:
        data = object_body(request.data) if request.data else {}
        message = data.get("message", "")
        if not isinstance(message, str):
            message = ""
        version = save_algorithm(get_algorithm(request.user, algorithm_id), request.user, message)
        return Response(version_payload(version))


class AlgorithmValidateView(APIView):
    def post(self, request: Request, algorithm_id) -> Response:
        algorithm = get_algorithm(request.user, algorithm_id)
        profile, _config = profile_for_algorithm(algorithm)
        compiled = compile_source(algorithm.source, profile)
        return Response(
            {"diagnostics": [diagnostic_payload(item) for item in compiled.diagnostics]}
        )


class VersionListView(APIView):
    def get(self, request: Request, algorithm_id) -> Response:
        algorithm = get_algorithm(request.user, algorithm_id)
        return _page(request, algorithm.versions.all(), version_payload)


class VersionRestoreView(APIView):
    def post(self, request: Request, algorithm_id, number: int) -> Response:
        version = restore_version(get_algorithm(request.user, algorithm_id), request.user, number)
        return Response(version_payload(version))


class ShareCreateView(APIView):
    def post(self, request: Request, algorithm_id) -> Response:
        algorithm = get_algorithm(request.user, algorithm_id)
        data = object_body(request.data) if request.data else {}
        link, token = create_share(
            request.user,
            algorithm=algorithm,
            expires_at=parse_expiry(data.get("expires_at")),
            ip_address=client_ip(request),
        )
        return Response(
            {"id": str(link.id), "token": token, "expires_at": link.expires_at},
            status=201,
        )


class ShareRevokeView(APIView):
    def delete(self, request: Request, link_id) -> Response:
        revoke_share(request.user, link_id)
        return Response(status=204)


@method_decorator(csrf_exempt, name="dispatch")
class SharedReadView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request: Request, token: str) -> Response:
        return Response(read_share(token))


def _page(request, queryset, serialize):
    paginator = TrazaPagination()
    page = paginator.paginate_queryset(queryset, request)
    return paginator.get_paginated_response([serialize(item) for item in page])
