from django.urls import path

from workers.views.workers import (
    WorkerCreateView,
    WorkerListView,
    WorkerRetrieveUpdateView,
)

app_Name = "workers"


urlpatterns = [
    path("create/", WorkerCreateView.as_view(), name="create"),
    path("<str:id>/", WorkerRetrieveUpdateView.as_view(), name="detail"),
    path("", WorkerListView.as_view(), name="list"),
]
