from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.classroom.services import (
    add_member,
    classroom_students,
    community_detail,
    create_community,
    delete_community,
    get_community,
    list_communities,
    person_payload,
    remove_member,
    search_people,
    set_community_translation,
    set_member_translation,
    student_projects,
)
from apps.http import client_ip, current_user, object_body


class CommunityListView(APIView):
    def get(self, request: Request) -> Response:
        return Response({"results": list_communities(current_user(request))})

    def post(self, request: Request) -> Response:
        community = create_community(
            current_user(request),
            object_body(request.data),
            client_ip(request),
        )
        return Response(community_detail(community), status=201)


class CommunityDetailView(APIView):
    def get(self, request: Request, community_id) -> Response:
        return Response(community_detail(get_community(current_user(request), community_id)))

    def patch(self, request: Request, community_id) -> Response:
        community = set_community_translation(
            current_user(request),
            community_id,
            object_body(request.data).get("translation_enabled"),
            client_ip(request),
        )
        return Response(community_detail(community))

    def delete(self, request: Request, community_id) -> Response:
        delete_community(current_user(request), community_id, client_ip(request))
        return Response(status=204)


class MemberListView(APIView):
    def post(self, request: Request, community_id) -> Response:
        data = object_body(request.data)
        member = add_member(
            current_user(request),
            community_id,
            data.get("user_id"),
            client_ip(request),
        )
        return Response(person_payload(member), status=201)


class MemberDetailView(APIView):
    def patch(self, request: Request, community_id, user_id: int) -> Response:
        community = set_member_translation(
            current_user(request),
            community_id,
            user_id,
            object_body(request.data).get("translation_enabled"),
            client_ip(request),
        )
        return Response(community_detail(community))

    def delete(self, request: Request, community_id, user_id: int) -> Response:
        remove_member(current_user(request), community_id, user_id, client_ip(request))
        return Response(status=204)


class ClassroomStudentListView(APIView):
    def get(self, request: Request) -> Response:
        return Response({"results": classroom_students(current_user(request))})


class ClassroomStudentProjectsView(APIView):
    def get(self, request: Request, user_id: int) -> Response:
        return Response(student_projects(current_user(request), user_id))


class PeopleSearchView(APIView):
    def get(self, request: Request) -> Response:
        people = search_people(
            current_user(request),
            request.query_params.get("q", ""),
            request.query_params.get("community"),
        )
        return Response({"results": people})
