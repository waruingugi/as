# consumers/probability.py

from commons.constants import CacheKeys, WebSocketChannels
from commons.websockets import BaseSnapshotConsumer


class ProbabilityConsumer(BaseSnapshotConsumer):
    """
    WebSocket consumer for streaming probability updates.
    - Auth + heartbeat via BaseAuthHeartbeatConsumer (inherited by BaseSnapshotConsumer)
    - Sends cached snapshot on connect
    - De-dupes updates by `updated_at`
    """

    def group_name_for(self, app: str) -> str:
        return WebSocketChannels.PROBABILITIES.format(app)

    def snapshot_cache_key_for(self, app: str) -> str:
        return CacheKeys.APP_PROBABILITY_SNAPSHOT.format(app)

    # channels handler wired by task's "type": "probability.update"
    async def probability_update(self, event):
        await self._handle_update(event)
