from django.urls import path

from analytics.views.websockets import ProbabilityConsumer

analytics_url_patterns = [
    path("ws/probabilities/<str:app>/", ProbabilityConsumer.as_asgi()),
]
