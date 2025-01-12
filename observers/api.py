from django.urls import include, path

from observers.routes import multipliers

urlpatterns = [path("multipliers/", include((multipliers.urlpatterns, "multipliers")))]
