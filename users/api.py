from django.urls import include, path

from users.routes import auth, users

urlpatterns = [
    path("auth/", include((auth.urlpatterns, "auth"))),
    path("users/", include((users.urlpatterns, "users"))),
]
