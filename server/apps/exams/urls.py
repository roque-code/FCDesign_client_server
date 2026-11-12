from django.urls import path

from apps.exams.views import (
    ExamAttemptView,
    ExamCloseView,
    ExamDetailView,
    ExamExportView,
    ExamFocusView,
    ExamGradesView,
    ExamGradeView,
    ExamImportView,
    ExamListView,
    ExamMineView,
    ExamNoticeView,
    ExamPublishView,
    ExamResultsView,
    ExamStartView,
    ExamSubmitView,
)

urlpatterns = [
    path("exams/", ExamListView.as_view(), name="exams"),
    path("exams/mine/", ExamMineView.as_view(), name="exams-mine"),
    path("exams/notices/", ExamNoticeView.as_view(), name="exams-notices"),
    path("exams/import/", ExamImportView.as_view(), name="exams-import"),
    path("exams/<uuid:exam_id>/", ExamDetailView.as_view(), name="exam"),
    path("exams/<uuid:exam_id>/publish/", ExamPublishView.as_view(), name="exam-publish"),
    path("exams/<uuid:exam_id>/close/", ExamCloseView.as_view(), name="exam-close"),
    path("exams/<uuid:exam_id>/export/", ExamExportView.as_view(), name="exam-export"),
    path("exams/<uuid:exam_id>/results/", ExamResultsView.as_view(), name="exam-results"),
    path("exams/<uuid:exam_id>/grades/", ExamGradesView.as_view(), name="exam-grades"),
    path("exams/<uuid:exam_id>/attempts/", ExamStartView.as_view(), name="exam-start"),
    path("exams/attempts/<uuid:attempt_id>/", ExamAttemptView.as_view(), name="exam-attempt"),
    path("exams/attempts/<uuid:attempt_id>/submit/", ExamSubmitView.as_view(), name="exam-submit"),
    path("exams/attempts/<uuid:attempt_id>/grade/", ExamGradeView.as_view(), name="exam-grade"),
    path("exams/attempts/<uuid:attempt_id>/focus/", ExamFocusView.as_view(), name="exam-focus"),
]
