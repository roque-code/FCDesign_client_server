from django.urls import path

from apps.language.views import KeywordView, MetaView

urlpatterns = [
    path("language/keywords/", KeywordView.as_view(), name="keywords"),
    path("meta/", MetaView.as_view(), name="meta"),
]
