from django.urls import path

from orchestrator.views.orchestrator import SeedSelectorView

app_name = "orchestrator"

urlpatterns = [
    path("seed-selector/", SeedSelectorView.as_view(), name="seed-selector"),
]
