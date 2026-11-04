from django.urls import path

from apps.chat.views import ChatBoardView, ChatConversationListView, ChatMessageListView

urlpatterns = [
    path("chat/board/", ChatBoardView.as_view(), name="chat-board"),
    path("chat/conversations/", ChatConversationListView.as_view(), name="chat-conversations"),
    path(
        "chat/conversations/<uuid:conversation_id>/messages/",
        ChatMessageListView.as_view(),
        name="chat-messages",
    ),
]
