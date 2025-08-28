import asyncio

from channels.db import database_sync_to_async

from commons.constants import (
    WEBSOCKET_MAX_LIFETIME_SECONDS,
    BettingApp,
    WebSocketChannels,
)
from commons.errors import ErrorCodes
from commons.utils import AuthJsonWebsocketConsumer
from observers.serializers import StrategySerializer, WorkerHistorySerializer
from observers.utils import get_strategy_data, get_workers_crash_history
from workers.models import Worker


class WorkerHistoryConsumer(AuthJsonWebsocketConsumer):
    keepalive_task = None
    max_lifetime_task = None

    MAX_LIFETIME_SECONDS = WEBSOCKET_MAX_LIFETIME_SECONDS

    async def connect(self):
        if not self.authenticate():
            await self.close()
            return

        self.app = self.scope["url_route"]["kwargs"]["app"]
        if self.app not in BettingApp.list():
            await self.close()
            return

        # NOTE: add a constant like "history_{0}" in WebSocketChannels
        self.group_name = WebSocketChannels.HISTORY.format(self.app)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Initial payload
        await self.send_history()

        # Hard max lifetime
        self.max_lifetime_task = asyncio.create_task(
            self._close_after(self.MAX_LIFETIME_SECONDS)
        )

    async def disconnect(self, close_code):
        # Cancel background tasks, don't leak
        for task in (self.keepalive_task, self.max_lifetime_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Best-effort cleanup; don't block on slow Redis
        try:
            await asyncio.wait_for(
                self.channel_layer.group_discard(self.group_name, self.channel_name),
                timeout=1.0,
            )
        except Exception:
            pass

    async def send_history(self):
        data = await self.get_history(self.app)
        await self.send_json(data)

    async def history_update(self, event):
        # Called via group_send(..., {"type": "history.update"})
        await self.send_history()

    @database_sync_to_async
    def get_history(self, app):
        # Ensure app exists / has workers
        if not Worker.objects.filter(app=app).exists():
            return {"error": ErrorCodes.WORKERS_NOT_FOUND.value}

        # If your util supports a `count` param, you can pull it from query string and pass it here.
        crash_history = get_workers_crash_history(app)
        serializer = WorkerHistorySerializer(crash_history, many=True)
        return serializer.data

    async def _close_after(self, seconds: int):
        try:
            await asyncio.sleep(seconds)
            await self.close(code=4000)  # custom close code
        except asyncio.CancelledError:
            pass


class StrategyConsumer(AuthJsonWebsocketConsumer):
    keepalive_task = None
    max_lifetime_task = None
    MAX_LIFETIME_SECONDS = WEBSOCKET_MAX_LIFETIME_SECONDS

    async def connect(self):
        if not self.authenticate():
            await self.close()
            return

        self.app = self.scope["url_route"]["kwargs"]["app"]
        if self.app not in BettingApp.list():
            await self.close()
            return

        self.group_name = WebSocketChannels.STRATEGY.format(self.app)

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Initial payload
        await self.send_strategy()

        # Hard max lifetime
        self.max_lifetime_task = asyncio.create_task(
            self._close_after(self.MAX_LIFETIME_SECONDS)
        )

    async def disconnect(self, close_code):
        # Cancel background tasks, don't leak
        for task in (self.keepalive_task, self.max_lifetime_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Best-effort cleanup; don't block on slow Redis
        try:
            await asyncio.wait_for(
                self.channel_layer.group_discard(self.group_name, self.channel_name),
                timeout=1.0,
            )
        except Exception:
            pass

    async def send_strategy(self):
        data = await self.get_strategy(self.app)
        await self.send_json(data)

    async def strategy_update(self, event):
        await self.send_strategy()

    @database_sync_to_async
    def get_strategy(self, app):
        if not Worker.objects.filter(app=app).exists():
            return {"error": ErrorCodes.WORKERS_NOT_FOUND.value}

        strategy = get_strategy_data(app)
        serializer = StrategySerializer(strategy, many=True)
        return serializer.data

    async def _close_after(self, seconds: int):
        try:
            await asyncio.sleep(seconds)
            await self.close(code=4000)  # custom close code
        except asyncio.CancelledError:
            pass
