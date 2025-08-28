from django.urls import path

from observers.views.websockets import StrategyConsumer, WorkerHistoryConsumer

multipliers_url_patterns = [
    path("ws/history/<str:app>/", WorkerHistoryConsumer.as_asgi()),
    path("ws/strategy/<str:app>/", StrategyConsumer.as_asgi()),
]
