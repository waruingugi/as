from django.urls import path
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.views import TokenRefreshView

from users.views.auth import (
    OTPVerificationView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendOTPVerificationView,
    UserTokenObtainPairView,
)

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
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-otp/", OTPVerificationView.as_view(), name="verify-otp"),
    path("resend-otp/", ResendOTPVerificationView.as_view(), name="resend-otp"),
    path(
        "password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
]
