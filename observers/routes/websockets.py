from django.urls import path

from observers.views.websockets import WorkerHistoryConsumer

multipliers_url_patterns = [
    path("ws/history/<str:app>/", WorkerHistoryConsumer.as_asgi()),
]
