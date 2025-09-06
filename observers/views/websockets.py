# consumers/strategy.py
from commons.constants import CacheKeys, WebSocketChannels
from commons.websockets import BaseSnapshotConsumer


class WorkerHistoryConsumer(BaseSnapshotConsumer):
    def group_name_for(self, app: str) -> str:
        return WebSocketChannels.HISTORY.format(app)

    def snapshot_cache_key_for(self, app: str) -> str:
        return CacheKeys.APP_HISTORY_SNAPSHOT.format(app)

    # channels handler wired by task's "type": "history.update"
    async def history_update(self, event):
        await self._handle_update(event)


class StrategyConsumer(BaseSnapshotConsumer):
    def group_name_for(self, app: str) -> str:
        return WebSocketChannels.STRATEGY.format(app)

    def snapshot_cache_key_for(self, app: str) -> str:
        return CacheKeys.APP_STRATEGY_SNAPSHOT.format(app)

    # channels handler wired by task's "type": "strategy.update"
    async def strategy_update(self, event):
        await self._handle_update(event)
