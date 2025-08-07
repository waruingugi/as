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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aviator.settings")

asgi_app = get_asgi_application()

# IMPORTANT: Ensure that the websocket_urlpatterns are imported after the Django settings are configured.
# This is necessary to avoid issues with the Django settings not being loaded when the websocket URL patterns
# are defined.
from aviator.websockets import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
