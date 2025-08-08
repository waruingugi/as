import asyncio

from channels.db import database_sync_to_async

from analytics.serializers import WorkerProbabilitySerializer
from analytics.utils import format_worker_probabilities
from commons.constants import BettingApp, WebSocketChannels
from commons.errors import ErrorCodes
from commons.utils import AuthJsonWebsocketConsumer
from workers.models import Worker


class ProbabilityConsumer(AuthJsonWebsocketConsumer):
    keepalive_task = None  # if you add keepalive below

    async def connect(self):
        # If authenticate() touches DB or cache, make it async and await it.
        # If it's pure header/JWT parsing, sync is fine.
        if not self.authenticate():
            # make sure to actually close if auth fails
            await self.close()
            return

        self.app = self.scope["url_route"]["kwargs"]["app"]
        if self.app not in BettingApp.list():
            await self.close()
            return

        self.group_name = WebSocketChannels.PROBABILITIES.format(self.app)

        # Join group first, then accept
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Initial payload
        await self.send_probabilities()

        # OPTIONAL: server-side keepalive (see below)
        # self.keepalive_task = asyncio.create_task(self._keepalive())

    async def disconnect(self, close_code):
        # Cancel background tasks first (if enabled)
        if self.keepalive_task:
            self.keepalive_task.cancel()
            try:
                await self.keepalive_task
            except asyncio.CancelledError:
                pass

        # Best-effort group discard with a short timeout
        try:
            await asyncio.wait_for(
                self.channel_layer.group_discard(self.group_name, self.channel_name),
                timeout=1.0,
            )
        except Exception:
            # swallow timeouts / redis hiccups; the channel will expire
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

    # OPTIONAL: keep the connection from idling out at proxies without client changes
    async def _keepalive(self):
        try:
            while True:
                await self.send_json({"type": "keepalive"})
                await asyncio.sleep(25)
        except asyncio.CancelledError:
            pass
