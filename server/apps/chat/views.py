from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Profile
from apps.chat.services import (
    lifetime_payload,
    list_board,
    list_messages,
    open_thread,
    send_message,
    update_lifetime,
)
from apps.http import current_user, object_body
from config.errors import DomainError


class MessageLifetimeView(APIView):
    def get(self, request: Request) -> Response:
        current_user(request)
        return Response(lifetime_payload())

    def patch(self, request: Request) -> Response:
        user = current_user(request)
        if user.profile.role != Profile.ADMIN:
            raise DomainError(
                "Solo un administrador puede definir la duración de los mensajes.",
                status_code=403,
            )
        return Response(lifetime_payload(update_lifetime(object_body(request.data))))


class ChatBoardView(APIView):
    def get(self, request: Request) -> Response:
        return Response(list_board(current_user(request), request.query_params.get("subject")))


class ChatConversationListView(APIView):
    def post(self, request: Request) -> Response:
        data = object_body(request.data)
        return Response(
            open_thread(
                current_user(request),
                data.get("subject"),
                data.get("community_id"),
                data.get("user_id"),
            )
        )


class ChatMessageListView(APIView):
    def get(self, request: Request, conversation_id) -> Response:
        return Response(list_messages(current_user(request), conversation_id))

    def post(self, request: Request, conversation_id) -> Response:
        message = send_message(current_user(request), conversation_id, object_body(request.data))
        return Response(message, status=201)
