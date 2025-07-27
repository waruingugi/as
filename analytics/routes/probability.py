from django.urls import path

from analytics.views.probability import (
    WorkerProbabilitiesView,
)

app_name = "probabilities"

urlpatterns = [
    path("<str:app>/", WorkerProbabilitiesView.as_view(), name="detail"),
]
