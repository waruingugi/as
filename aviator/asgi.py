"""
ASGI config for aviator project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

#
# import os
#
# from django.core.asgi import get_asgi_application
#
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aviator.settings")
#
# application = get_asgi_application()

# asgi.py
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from aviator.websockets import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aviator.settings")

asgi_app = get_asgi_application()

# Websocket URL patterns
# ruff E402 ignored: from analytics.api import (
#     websocket_urlpatterns,
# )

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
