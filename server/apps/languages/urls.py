from django.urls import path

from apps.languages.views import (
    LanguageCloseView,
    LanguageInputView,
    LanguageOpenView,
    LanguagePollView,
    LanguageRunView,
    LanguageStatusView,
)

urlpatterns = [
    path("languages/status/", LanguageStatusView.as_view(), name="language-status"),
    path("languages/run/", LanguageRunView.as_view(), name="language-run"),
    path("languages/open/", LanguageOpenView.as_view(), name="language-open"),
    path("languages/input/", LanguageInputView.as_view(), name="language-input"),
    path("languages/poll/", LanguagePollView.as_view(), name="language-poll"),
    path("languages/close/", LanguageCloseView.as_view(), name="language-close"),
]
