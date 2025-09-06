"""
ASGI config for aviator project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aviator.settings")

asgi_app = get_asgi_application()

# IMPORTANT: Ensure that the websocket_urlpatterns are imported after the Django settings are configured.
# This is necessary to avoid issues with the Django settings not being loaded when the websocket URL patterns
# are defined.
from aviator.websockets import websocket_urlpatterns  # noqa: E402
from commons.middlewares import JwtAuthWebsocketMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": asgi_app,
        "websocket": JwtAuthWebsocketMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
