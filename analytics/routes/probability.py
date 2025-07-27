from django.urls import path, re_path

from analytics.views.probability import (
    ProbabilityConsumer,
    WorkerProbabilitiesView,
)

app_name = "probabilities"

urlpatterns = [
    path("<str:app>/", WorkerProbabilitiesView.as_view(), name="detail"),
]


websocket_urlpatterns = [
    re_path(r"ws/probabilities/(?P<app>\w+)/$", ProbabilityConsumer.as_asgi()),
]
