from django.urls import path

from analytics.views.probability import (
    WorkerProbabilitiesStreamView,
    WorkerProbabilitiesView,
)

app_name = "probabilities"

urlpatterns = [
    path("<str:app>/", WorkerProbabilitiesView.as_view(), name="detail"),
    path(
        "<str:app>/stream/",
        WorkerProbabilitiesStreamView.as_view(),
        name="stream",
    ),
]
