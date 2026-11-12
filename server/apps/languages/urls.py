from django.urls import path

from apps.languages.views import (
    LanguageCheckView,
    LanguageCloseView,
    LanguageInputView,
    LanguageOpenView,
    LanguagePollView,
    LanguageRunView,
    LanguageStatusView,
    ProgramDetailView,
    ProgramListView,
    StudentProgramsView,
)

urlpatterns = [
    path("languages/status/", LanguageStatusView.as_view(), name="language-status"),
    path("languages/run/", LanguageRunView.as_view(), name="language-run"),
    path("languages/open/", LanguageOpenView.as_view(), name="language-open"),
    path("languages/check/", LanguageCheckView.as_view(), name="language-check"),
    path("languages/input/", LanguageInputView.as_view(), name="language-input"),
    path("languages/poll/", LanguagePollView.as_view(), name="language-poll"),
    path("languages/close/", LanguageCloseView.as_view(), name="language-close"),
    path("languages/programs/", ProgramListView.as_view(), name="language-programs"),
    path(
        "languages/programs/<uuid:program_id>/",
        ProgramDetailView.as_view(),
        name="language-program",
    ),
    path(
        "classroom/students/<int:user_id>/programs/",
        StudentProgramsView.as_view(),
        name="classroom-student-programs",
    ),
]
