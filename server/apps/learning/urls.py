from django.urls import path

from apps.learning.authoring_views import (
    AuthoredAssignmentsView,
    AuthoredChallengeCollectionView,
    AuthoredChallengeEditorView,
    AuthoredChallengesView,
    AuthoredDetailView,
    AuthoredEntryView,
    AuthoredListView,
    BankView,
    CatalogView,
    ChallengeCsvView,
)
from apps.learning.course_views import (
    AttemptCheckView,
    AttemptCloseView,
    AttemptExpireView,
    AttemptHintView,
    AttemptLanguageView,
    AttemptRunView,
    AttemptStageView,
    AttemptStartView,
    ChallengeDetailView,
    MemberProgressView,
    MemberWorkView,
    PathsView,
    PathView,
    RosterProgressView,
    RosterView,
)
from apps.learning.practice_views import PracticeDetailView, PracticeListView
from apps.learning.views import (
    ImportView,
    PreviewView,
    RunControlView,
    RunDetailView,
    RunEventsView,
    RunInputView,
    RunStartView,
)

urlpatterns = [
    path("learning/path/", PathView.as_view(), name="learning-path"),
    path("learning/paths/", PathsView.as_view(), name="learning-paths"),
    path("learning/catalog/", CatalogView.as_view(), name="learning-catalog"),
    path("learning/bank/", BankView.as_view(), name="learning-bank"),
    path("learning/challenges/csv/", ChallengeCsvView.as_view(), name="learning-challenge-csv"),
    path("learning/authored/", AuthoredListView.as_view(), name="learning-authored"),
    path(
        "learning/authored/challenges/",
        AuthoredChallengeCollectionView.as_view(),
        name="learning-authored-challenge-create",
    ),
    path(
        "learning/authored/challenges/<uuid:challenge_id>/",
        AuthoredChallengeEditorView.as_view(),
        name="learning-authored-challenge",
    ),
    path(
        "learning/authored/<uuid:path_id>/",
        AuthoredDetailView.as_view(),
        name="learning-authored-detail",
    ),
    path(
        "learning/authored/<uuid:path_id>/challenges/",
        AuthoredChallengesView.as_view(),
        name="learning-authored-challenges",
    ),
    path(
        "learning/authored/<uuid:path_id>/challenges/<uuid:challenge_id>/",
        AuthoredEntryView.as_view(),
        name="learning-authored-entry",
    ),
    path(
        "learning/authored/<uuid:path_id>/assignments/",
        AuthoredAssignmentsView.as_view(),
        name="learning-authored-assignments",
    ),
    path("learning/roster/", RosterView.as_view(), name="learning-roster"),
    path(
        "learning/roster/<uuid:path_id>/progress/",
        RosterProgressView.as_view(),
        name="learning-roster-progress",
    ),
    path(
        "learning/roster/<int:user_id>/",
        MemberProgressView.as_view(),
        name="learning-member-progress",
    ),
    path(
        "learning/roster/<int:user_id>/challenges/<uuid:challenge_id>/",
        MemberWorkView.as_view(),
        name="learning-member-work",
    ),
    path(
        "learning/challenges/<uuid:challenge_id>/",
        ChallengeDetailView.as_view(),
        name="learning-challenge",
    ),
    path(
        "learning/challenges/<uuid:challenge_id>/attempts/",
        AttemptStartView.as_view(),
        name="learning-attempt-start",
    ),
    path(
        "learning/attempts/<uuid:attempt_id>/stage/",
        AttemptStageView.as_view(),
        name="learning-attempt-stage",
    ),
    path(
        "learning/attempts/<uuid:attempt_id>/hint/",
        AttemptHintView.as_view(),
        name="learning-attempt-hint",
    ),
    path(
        "learning/attempts/<uuid:attempt_id>/check/",
        AttemptCheckView.as_view(),
        name="learning-attempt-check",
    ),
    path(
        "learning/attempts/<uuid:attempt_id>/run/",
        AttemptRunView.as_view(),
        name="learning-attempt-run",
    ),
    path(
        "learning/attempts/<uuid:attempt_id>/expire/",
        AttemptExpireView.as_view(),
        name="learning-attempt-expire",
    ),
    path(
        "learning/attempts/<uuid:attempt_id>/language/",
        AttemptLanguageView.as_view(),
        name="learning-attempt-language",
    ),
    path(
        "learning/attempts/<uuid:attempt_id>/close/",
        AttemptCloseView.as_view(),
        name="learning-attempt-close",
    ),
    path("learning/practices/", PracticeListView.as_view(), name="learning-practices"),
    path(
        "learning/practices/<uuid:practice_id>/",
        PracticeDetailView.as_view(),
        name="learning-practice",
    ),
    path("learning/preview/", PreviewView.as_view(), name="learning-preview"),
    path("learning/import/", ImportView.as_view(), name="learning-import"),
    path("learning/run/", RunStartView.as_view(), name="learning-run"),
    path("learning/runs/<uuid:run_id>/", RunDetailView.as_view(), name="learning-run-detail"),
    path(
        "learning/runs/<uuid:run_id>/events/", RunEventsView.as_view(), name="learning-run-events"
    ),
    path(
        "learning/runs/<uuid:run_id>/control/",
        RunControlView.as_view(),
        name="learning-run-control",
    ),
    path("learning/runs/<uuid:run_id>/input/", RunInputView.as_view(), name="learning-run-input"),
]
