from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.views import TokenRefreshView

from users.views.auth import UserTokenObtainPairView

# Extend the schema for the TokenRefreshView
TokenRefreshView = extend_schema_view(  # type: ignore
    post=extend_schema(
        tags=["auth"],
    )
)(TokenRefreshView)

app_name = "auth"

urlpatterns = [
    path("login/", UserTokenObtainPairView.as_view(), name="obtain-token"),
    path("token/refresh/", TokenRefreshView.as_view(), name="refresh-token"),
]
