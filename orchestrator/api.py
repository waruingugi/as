from django.urls import include, path

from orchestrator.routes import orchestrator

urlpatterns = [
    path("orchestrator/", include((orchestrator.urlpatterns, "orchestrator")))
]
