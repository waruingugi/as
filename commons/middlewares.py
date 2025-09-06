import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http.response import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from log_request_id import local
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
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

    EXEMPT_PATHS = [
        "/api/multipliers/create/",
    ]

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

        if request.get_full_path() not in self.EXEMPT_PATHS:
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

        if request.get_full_path() not in self.EXEMPT_PATHS:
            logger.info(f"Response: {local.request_id}: {response_log_data}")

        return response


class JwtAuthWebsocketMiddleware(BaseMiddleware):
    # Entry point for the middleware, called for each WebSocket connection
    async def __call__(self, scope, receive, send):
        # Extract JWT token from headers or query string
        token = self._extract_token(scope)
        # Get user from token asynchronously, or set as AnonymousUser if not found
        user = await self._user_from_token(token) if token else None
        scope["user"] = user or AnonymousUser()

        # Continue processing the connection
        return await super().__call__(scope, receive, send)

    # Extracts the JWT token from the connection scope
    def _extract_token(self, scope) -> str | None:
        headers = dict(scope.get("headers", []))
        auth = headers.get(b"authorization")
        if auth:
            return auth.decode("utf-8")  # e.g. "Bearer eyJ..."

        # Fallback: check for token in query string
        qs = parse_qs((scope.get("query_string") or b"").decode())
        if "token" in qs:
            return f"Bearer {qs['token'][0]}"
        return None

    # Retrieves the user associated with the JWT token (runs in DB thread)
    @database_sync_to_async
    def _user_from_token(self, token_or_header: str):
        try:
            jwt_auth = JWTAuthentication()
            parts = token_or_header.split()
            raw = parts[-1] if len(parts) >= 2 else parts[0]
            validated = jwt_auth.get_validated_token(raw.encode("utf-8"))
            return jwt_auth.get_user(validated)
        except InvalidToken:
            return None
        except get_user_model().DoesNotExist:
            return None
