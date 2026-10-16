from django.urls import path

from apps.projects.views import (
    AlgorithmDetailView,
    AlgorithmListView,
    AlgorithmSaveView,
    AlgorithmTranslateView,
    AlgorithmValidateView,
    FolderDetailView,
    FolderListView,
    ProjectDetailView,
    ProjectListView,
    ProjectRestoreView,
    ShareCreateView,
    SharedReadView,
    ShareRevokeView,
    VersionListView,
    VersionRestoreView,
)

urlpatterns = [
    path("projects/", ProjectListView.as_view(), name="projects"),
    path("projects/<uuid:project_id>/", ProjectDetailView.as_view(), name="project-detail"),
    path(
        "projects/<uuid:project_id>/restore/", ProjectRestoreView.as_view(), name="project-restore"
    ),
    path("projects/<uuid:project_id>/folders/", FolderListView.as_view(), name="folders"),
    path("folders/<uuid:folder_id>/", FolderDetailView.as_view(), name="folder-detail"),
    path("algorithms/", AlgorithmListView.as_view(), name="algorithms"),
    path("algorithms/<uuid:algorithm_id>/", AlgorithmDetailView.as_view(), name="algorithm-detail"),
    path(
        "algorithms/<uuid:algorithm_id>/save/", AlgorithmSaveView.as_view(), name="algorithm-save"
    ),
    path(
        "algorithms/<uuid:algorithm_id>/validate/",
        AlgorithmValidateView.as_view(),
        name="algorithm-validate",
    ),
    path(
        "algorithms/<uuid:algorithm_id>/translate/",
        AlgorithmTranslateView.as_view(),
        name="algorithm-translate",
    ),
    path(
        "algorithms/<uuid:algorithm_id>/versions/",
        VersionListView.as_view(),
        name="algorithm-versions",
    ),
    path(
        "algorithms/<uuid:algorithm_id>/versions/<int:number>/restore/",
        VersionRestoreView.as_view(),
        name="algorithm-version-restore",
    ),
    path(
        "algorithms/<uuid:algorithm_id>/share/", ShareCreateView.as_view(), name="algorithm-share"
    ),
    path("share-links/<uuid:link_id>/", ShareRevokeView.as_view(), name="share-revoke"),
    path("shared/<str:token>/", SharedReadView.as_view(), name="shared"),
]
