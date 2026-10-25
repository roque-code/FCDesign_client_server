from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView

from config.health import HealthView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.billing.urls")),
    path("api/v1/", include("apps.projects.urls")),
    path("api/v1/", include("apps.executions.urls")),
    path("api/v1/", include("apps.flowcharts.urls")),
    path("api/v1/", include("apps.editor.urls")),
    path("api/v1/", include("apps.language.urls")),
    path("api/v1/", include("apps.classroom.urls")),
    path("api/v1/", include("apps.learning.urls")),
    path("api/v1/", include("apps.languages.urls")),
]
