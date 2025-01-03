from django.urls import include, path

from users.routes import users

urlpatterns = [
    path("users/", include((users.urlpatterns, "users"))),
]
