from django.urls import include, path

from workers.routes import workers

urlpatterns = [
    path("workers/", include((workers.urlpatterns, "workers"))),
]
