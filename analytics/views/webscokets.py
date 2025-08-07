from channels.db import database_sync_to_async

from analytics.serializers import WorkerProbabilitySerializer
from analytics.utils import format_worker_probabilities
from commons.constants import BettingApp, WebSocketChannels
from commons.errors import ErrorCodes
from commons.utils import AuthJsonWebsocketConsumer
from workers.models import Worker


class ProbabilityConsumer(AuthJsonWebsocketConsumer):
    async def connect(self):
        if not self.authenticate():
            return

        self.app = self.scope["url_route"]["kwargs"]["app"]
        if self.app not in BettingApp.list():
            await self.close()
            return

        self.group_name = WebSocketChannels.PROBABILITIES.format(self.app)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_probabilities()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_probabilities(self):
        data = await self.get_worker_probabilities(self.app)
        await self.send_json(data)

    async def probability_update(self, event):
        await self.send_probabilities()

    @database_sync_to_async
    def get_worker_probabilities(self, app):
        workers = Worker.objects.filter(app=app)
        if not workers.exists():
            return {"error": ErrorCodes.WORKERS_NOT_FOUND.value}

        response_data = [format_worker_probabilities(w) for w in workers]
        serializer = WorkerProbabilitySerializer(response_data, many=True)
        return serializer.data
