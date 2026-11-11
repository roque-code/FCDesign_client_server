from django.urls import path

from apps.classroom.views import (
    ClassroomGradesView,
    ClassroomStudentListView,
    ClassroomStudentProjectsView,
    CommunityCodeView,
    CommunityDetailView,
    CommunityJoinView,
    CommunityListView,
    ExerciseFeedbackView,
    MemberDetailView,
    MemberListView,
    MyFeedbackView,
    PeopleSearchView,
)

urlpatterns = [
    path("communities/", CommunityListView.as_view(), name="communities"),
    path("communities/join/", CommunityJoinView.as_view(), name="community-join"),
    path("communities/<uuid:community_id>/", CommunityDetailView.as_view(), name="community"),
    path(
        "communities/<uuid:community_id>/code/",
        CommunityCodeView.as_view(),
        name="community-code",
    ),
    path(
        "communities/<uuid:community_id>/members/",
        MemberListView.as_view(),
        name="community-members",
    ),
    path(
        "communities/<uuid:community_id>/members/<int:user_id>/",
        MemberDetailView.as_view(),
        name="community-member",
    ),
    path("people/", PeopleSearchView.as_view(), name="people"),
    path("classroom/students/", ClassroomStudentListView.as_view(), name="classroom-students"),
    path(
        "classroom/students/<int:user_id>/projects/",
        ClassroomStudentProjectsView.as_view(),
        name="classroom-student-projects",
    ),
    path(
        "classroom/feedback/<str:kind>/<uuid:exercise_id>/",
        ExerciseFeedbackView.as_view(),
        name="classroom-feedback",
    ),
    path("classroom/grades/", ClassroomGradesView.as_view(), name="classroom-grades"),
    path("feedback/", MyFeedbackView.as_view(), name="my-feedback"),
]
