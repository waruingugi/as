from django.urls import path

from observers.views.history import WorkerHistoryView
from observers.views.multipliers import MultiplierCreateView, MultiplierListView

app_name = "multipliers"

urlpatterns = [
    path("create/", MultiplierCreateView.as_view(), name="create"),
    path("", MultiplierListView.as_view(), name="list"),
    path("history/<str:app>/", WorkerHistoryView.as_view(), name="history"),
]

# websocket_urlpatterns = [
#     re_path(r"ws/history/(?P<app>\w+)/$", WorkerHistoryConsumer.as_asgi()),
# ]
