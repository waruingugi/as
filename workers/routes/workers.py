from django.urls import path

from workers.views.workers import WorkerCreateView

app_Name = "workers"


urlpatterns = [
    path("create/", WorkerCreateView.as_view(), name="create"),
]
