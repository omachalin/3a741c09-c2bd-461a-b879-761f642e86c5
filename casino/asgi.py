"""
ASGI config for casino project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import warnings

# Suppress GIL warnings for msgpack on Python 3.14t
warnings.filterwarnings("ignore", category=RuntimeWarning, module="msgpack._cmsgpack")
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'casino.settings')
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack
from game.routing import websocket_urlpatterns
from channels.routing import ProtocolTypeRouter, URLRouter

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
