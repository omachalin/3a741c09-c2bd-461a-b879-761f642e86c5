import json
from channels.generic.websocket import AsyncWebsocketConsumer

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(
            "games",
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            "games",
            self.channel_name
        )

    async def game_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': event['type'],
            'data': event['data']
        }))
