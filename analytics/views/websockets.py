import asyncio

from channels.db import database_sync_to_async

from analytics.serializers import WorkerProbabilitySerializer
from analytics.utils import format_worker_probabilities
from commons.constants import (
    WEBSOCKET_MAX_LIFETIME_SECONDS,
    BettingApp,
    WebSocketChannels,
)
from commons.errors import ErrorCodes
from commons.utils import AuthJsonWebsocketConsumer
from workers.models import Worker


class ProbabilityConsumer(AuthJsonWebsocketConsumer):
    keepalive_task = None
    max_lifetime_task = None  # hard max lifetime task

    MAX_LIFETIME_SECONDS = WEBSOCKET_MAX_LIFETIME_SECONDS

    async def connect(self):
        if not self.authenticate():
            await self.close()
            return

        self.app = self.scope["url_route"]["kwargs"]["app"]
        if self.app not in BettingApp.list():
            await self.close()
            return

        self.group_name = WebSocketChannels.PROBABILITIES.format(self.app)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send first payload
        await self.send_probabilities()

        # Start hard max lifetime countdown
        self.max_lifetime_task = asyncio.create_task(
            self._close_after(self.MAX_LIFETIME_SECONDS)
        )

    async def disconnect(self, close_code):
        # Cancel background tasks
        for task in (self.keepalive_task, self.max_lifetime_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Group cleanup
        try:
            await asyncio.wait_for(
                self.channel_layer.group_discard(self.group_name, self.channel_name),
                timeout=1.0,
            )
        except Exception:
            pass

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

    async def _close_after(self, seconds: int):
        try:
            await asyncio.sleep(seconds)
            await self.close(code=4000)  # custom close code
        except asyncio.CancelledError:
            pass
