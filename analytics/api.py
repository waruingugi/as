from django.urls import include, path

from analytics.routes import probability

urlpatterns = [
    path("probabilities/", include((probability.urlpatterns, "probabilities"))),
]
