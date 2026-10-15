from django.urls import path

from apps.editor.views import PreferenceView

urlpatterns = [
    path("preferences/", PreferenceView.as_view(), name="preferences"),
]
