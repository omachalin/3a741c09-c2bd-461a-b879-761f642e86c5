from django.urls import path
from channels.routing import URLRouter
from game import routing as game_routing

websocket_urlpatterns = [
    path('ws/', URLRouter(game_routing.websocket_urlpatterns)),
]
