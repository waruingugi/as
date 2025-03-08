from django.urls import path

from workers.views.workers import (
    WorkerCreateView,
    WorkerListView,
    WorkerRetrieveUpdateView,
    WorkersHealthView,
)

app_name = "workers"


urlpatterns = [
    path("create/", WorkerCreateView.as_view(), name="create"),
    path("<str:id>/", WorkerRetrieveUpdateView.as_view(), name="detail"),
    path("health/<str:app>/", WorkersHealthView.as_view(), name="health"),
    path("", WorkerListView.as_view(), name="list"),
]
