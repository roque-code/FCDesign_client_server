from django.urls import path

from apps.flowcharts.views import FlowchartView

urlpatterns = [
    path(
        "algorithms/<uuid:algorithm_id>/flowchart/",
        FlowchartView.as_view(),
        name="algorithm-flowchart",
    ),
]
