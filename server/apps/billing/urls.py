from django.urls import path

from apps.billing.views import (
    CatalogView,
    ConnectedSessionView,
    ConsumeExecutionView,
    PlanDetailView,
    PlanListView,
    SubscriberDetailView,
    SubscriberListView,
)

urlpatterns = [
    path("usage/execution/", ConsumeExecutionView.as_view(), name="usage-execution"),
    path("billing/catalog/", CatalogView.as_view(), name="billing-catalog"),
    path("billing/plans/", PlanListView.as_view(), name="billing-plans"),
    path("billing/plans/<uuid:plan_id>/", PlanDetailView.as_view(), name="billing-plan"),
    path("billing/sessions/", ConnectedSessionView.as_view(), name="billing-sessions"),
    path("billing/users/", SubscriberListView.as_view(), name="billing-users"),
    path("billing/users/<int:user_id>/", SubscriberDetailView.as_view(), name="billing-user"),
]
