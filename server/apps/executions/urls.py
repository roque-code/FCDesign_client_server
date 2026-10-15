from django.urls import path

from apps.executions.views import (
    DebugView,
    ExecuteView,
    ExecutionControlView,
    ExecutionDetailView,
    ExecutionEventsView,
    ExecutionInputView,
    ExecutionInspectView,
)

urlpatterns = [
    path("algorithms/<uuid:algorithm_id>/execute/", ExecuteView.as_view(), name="execute"),
    path("algorithms/<uuid:algorithm_id>/debug/", DebugView.as_view(), name="debug"),
    path("executions/<uuid:execution_id>/", ExecutionDetailView.as_view(), name="execution-detail"),
    path(
        "executions/<uuid:execution_id>/input/",
        ExecutionInputView.as_view(),
        name="execution-input",
    ),
    path(
        "executions/<uuid:execution_id>/control/",
        ExecutionControlView.as_view(),
        name="execution-control",
    ),
    path(
        "executions/<uuid:execution_id>/events/",
        ExecutionEventsView.as_view(),
        name="execution-events",
    ),
    path(
        "executions/<uuid:execution_id>/inspect/",
        ExecutionInspectView.as_view(),
        name="execution-inspect",
    ),
]
