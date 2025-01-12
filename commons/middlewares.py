import json

from django.contrib.auth import get_user_model
from django.http.response import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from log_request_id import local
from rest_framework import status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from commons.logger import logger

User = get_user_model()


class UserIsActiveMiddleware(MiddlewareMixin):
    """Log out inactive users."""

    def process_request(self, request) -> None | JsonResponse:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

            try:
                # Decode the token
                access_token = AccessToken(token)
                user = User.objects.get(id=access_token["user_id"])

                if not user.is_active:
                    # Invalidate the token
                    try:
                        token = RefreshToken(token)
                        token.blacklist()
                    except TokenError:
                        pass

                    # Logout the user
                    return JsonResponse(
                        {"detail": "This account is inactive."},
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

            except (TokenError, User.DoesNotExist):
                return JsonResponse(
                    {"detail": "Invalid token."}, status=status.HTTP_401_UNAUTHORIZED
                )

        return None


class RequestResponseLoggerMiddleware(MiddlewareMixin):
    """Log incoming requests and outgoing responses."""

    def process_request(self, request):
        exclude_keys = ["Authorization", "Cookie"]
        sensitive_keys_data = ["refresh", "access", "password"]

        # Create a new dictionary excluding the sensitive data
        headers = {k: v for k, v in request.headers.items() if k not in exclude_keys}

        # Pop sensitive key data
        data = {}
        if request.content_type == "application/json" and request.method in [
            "POST",
            "PUT",
            "PATCH",
        ]:
            try:
                data = json.loads(request.body)
                data = {k: v for k, v in data.items() if k not in sensitive_keys_data}
            except json.JSONDecodeError:
                pass

        log_data = {
            "method": request.method,
            "headers": headers,
            "path": request.get_full_path(),
            "user_id": (
                str(request.user.id) if request.user.is_authenticated else "Anonymous"
            ),
            "ip_address": request.META.get("HTTP_FLY_CLIENT_IP")
            or request.META.get("REMOTE_ADDR"),
            "data": data,
        }
        logger.info(
            f"Request: {local.request_id} - {log_data['ip_address']}: {log_data}"
        )

    def process_response(self, request, response):
        response_log_data = dict(
            status_code=response.status_code,
            user_id=(
                str(request.user.id) if request.user.is_authenticated else "Anonymous"
            ),
        )
        logger.info(f"Response: {local.request_id}: {response_log_data}")

        return response
