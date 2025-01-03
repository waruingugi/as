from django.urls import path

from workers.views.workers import (
    WorkerCreateView,
    WorkerListView,
    WorkerRetrieveUpdateView,
)

app_Name = "workers"


urlpatterns = [
    path("create/", WorkerCreateView.as_view(), name="create"),
    path("update/", WorkerRetrieveUpdateView.as_view(), name="update"),
    path("list/", WorkerListView.as_view(), name="list"),
]
