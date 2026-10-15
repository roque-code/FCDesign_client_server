from django.urls import path

from apps.classroom.views import (
    CommunityDetailView,
    CommunityListView,
    MemberDetailView,
    MemberListView,
    PeopleSearchView,
)

urlpatterns = [
    path("communities/", CommunityListView.as_view(), name="communities"),
    path("communities/<uuid:community_id>/", CommunityDetailView.as_view(), name="community"),
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
]
