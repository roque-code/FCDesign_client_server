from django.urls import path

from apps.chat.views import MessageLifetimeView

urlpatterns = [
    path("message-lifetime/", MessageLifetimeView.as_view(), name="message-lifetime"),
]
