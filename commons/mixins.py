from channels.db import database_sync_to_async
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class AsyncWebSocketAuthMixin:
    def get_token_from_scope(self) -> str:
        """Extracts the JWT token from the WebSocket scope headers."""
        headers = dict(self.scope["headers"])
        if b"authorization" not in headers:
            raise AuthenticationFailed("No authorization header")
        return headers[b"authorization"].decode("utf-8")

    @database_sync_to_async
    def authenticate_user(self) -> object:
        """Authenticates the user using the JWT token from the WebSocket scope."""
        token = self.get_token_from_scope()
        jwt_auth = JWTAuthentication()
        request = type("Request", (), {"META": {"HTTP_AUTHORIZATION": token}})
        user_auth_tuple = jwt_auth.authenticate(request)
        if user_auth_tuple is None:
            raise AuthenticationFailed("Invalid token")
        return user_auth_tuple[0]
