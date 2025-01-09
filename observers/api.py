from django.urls import include, path

from observers.routes import multipliers

urlpatterns = [path("observers/", include((multipliers.urlpatterns, "multipliers")))]
