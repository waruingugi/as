import asyncio
import contextlib
import time
from typing import Any, Dict, Optional, Set

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache

from commons.constants import BettingApp


class BaseAuthHeartbeatConsumer(AsyncJsonWebsocketConsumer):
    """
    Base WebSocket consumer with authentication and heartbeat support.

    Features:
      - Requires authentication on connect (unless `require_auth` is set to False).
      - Sends periodic heartbeat pings to the client.
      - Closes the connection if the client misses a configurable number of pongs.
      - Provides hooks for subclasses: on_connect, on_message, on_disconnect.
      - Helper methods to join/leave groups with automatic cleanup.
    """

    require_auth: bool = True  # Set to False in subclass to allow anonymous connections

    # ---- heartbeat configuration ----
    HEARTBEAT_INTERVAL: int = 60  # Seconds between heartbeat pings
    MISSED_PONG_LIMIT: int = 2  # Number of missed pongs before closing connection
    HEARTBEAT_GRACE: int = 10  # Additional grace period in seconds

    heartbeat_task: Optional[asyncio.Task] = None  # Background task for heartbeat loop
    last_pong_time: float = 0.0  # Timestamp of last received pong
    joined_groups: Set[str]  # Set of group names this consumer has joined

    # NEW: ensure attrs exist even if disconnect fires before connect
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.last_pong_time: float = time.monotonic()
        self.joined_groups: Set[str] = set()

    # ---------- lifecycle ----------

    async def connect(self):
        """
        Called when a WebSocket connection is opened.
        Checks authentication, initializes state, and starts the heartbeat loop.
        """
        user = self.scope.get("user")
        if self.require_auth and (not user or getattr(user, "is_anonymous", True)):
            await self.close(code=4401)  # Unauthorized
            return

        self.joined_groups = set()
        self.last_pong_time = time.monotonic()

        await self.accept()
        # Start the heartbeat loop in the background
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Hook for subclasses (e.g., join groups, send initial snapshot)
        await self.on_connect()

    async def disconnect(self, code):
        """
        Called when the WebSocket connection is closed.
        Stops the heartbeat loop and leaves all joined groups.
        """
        # Stop the heartbeat loop
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            with contextlib.suppress(Exception):
                await self.heartbeat_task

        # Leave all joined groups
        for group in list(self.joined_groups):
            with contextlib.suppress(Exception):
                await self.channel_layer.group_discard(group, self.channel_name)
        self.joined_groups.clear()

        # Subclass hook for additional cleanup
        await self.on_disconnect(code)

    # ---------- hooks for subclasses ----------

    async def on_connect(self) -> None:
        """
        Hook for subclasses: called after successful connection.
        Override to join groups, send initial data, etc.
        """
        return

    async def on_message(self, content: Dict[str, Any]) -> None:
        """
        Hook for subclasses: called when a non-heartbeat message is received.
        Override to handle app-specific client messages.
        """
        return

    async def on_disconnect(self, code: int) -> None:
        """
        Hook for subclasses: called after disconnect for extra cleanup.
        """
        return

    # ---------- client → server messages ----------

    async def receive_json(self, content, **kwargs):
        """
        Handles incoming JSON messages from the client.
        Processes heartbeat pongs and delegates other messages to on_message.
        """
        msg_type = content.get("type")

        if msg_type == "pong":
            # Client acknowledged our ping; update last_pong_time
            self.last_pong_time = time.monotonic()
            return

        # (Optional) If you want to handle client-initiated ping:
        # if msg_type == "ping":
        #     await self.send_json({"type": "pong", "ts": time.time()})
        #     self.last_pong_time = time.monotonic()
        #     return

        await self.on_message(content)

    # ---------- server heartbeat ----------

    async def _heartbeat_loop(self):
        """
        Periodically sends heartbeat pings to the client.
        Closes the connection if too many pongs are missed.
        """
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)

                # Check if the client has missed too many pongs
                silent_duration = time.monotonic() - self.last_pong_time
                allowed_silence = (
                    self.HEARTBEAT_INTERVAL * self.MISSED_PONG_LIMIT
                    + self.HEARTBEAT_GRACE
                )
                if silent_duration > allowed_silence:
                    await self.close(code=4001)  # Custom "policy" close code
                    break

                # Send a ping; if this fails, the socket is already closed
                await self.send_json({"type": "ping", "timestamp": time.time()})
        except asyncio.CancelledError:
            # Task was cancelled (e.g., on disconnect)
            pass
        except Exception:
            # Socket likely closed; ignore other exceptions
            pass

    # ---------- helpers for subclasses ----------

    async def join_group(self, name: str) -> None:
        """
        Adds this consumer to a channel layer group and tracks the group for cleanup.
        """
        await self.channel_layer.group_add(name, self.channel_name)
        self.joined_groups.add(name)

    async def leave_group(self, name: str) -> None:
        """
        Removes this consumer from a channel layer group and updates tracking.
        """
        if name in self.joined_groups:
            await self.channel_layer.group_discard(name, self.channel_name)
            self.joined_groups.discard(name)


class BaseSnapshotConsumer(BaseAuthHeartbeatConsumer):
    """
    Base consumer for sending an initial data snapshot on connect and handling incremental updates.

    Subclasses must implement:
      \- group_name_for(app: str) -> str: Returns the group name for a given app.
      \- snapshot_cache_key_for(app: str) -> str: Returns the cache key for the app's snapshot.
      \- A channels event handler that calls `await self._handle_update(event)` for updates.

    Features:
      \- Sends the latest cached snapshot to the client upon connection.
      \- Listens for and delivers incremental updates based on `updated_at` timestamps.
      \- Ignores stale or duplicate updates.
    """

    _last_updated_at = 0

    # ---- hooks to implement in subclasses ----
    def group_name_for(self, app: str) -> str:  # pragma: no cover
        raise NotImplementedError

    def snapshot_cache_key_for(self, app: str) -> str:  # pragma: no cover
        raise NotImplementedError

    # ---- lifecycle ----
    async def on_connect(self):
        app = self.scope["url_route"]["kwargs"]["app"]
        if app not in BettingApp.list():
            await self.close()
            return

        self.app = app
        self.group = self.group_name_for(app)
        await self.join_group(self.group)

        # Send latest cached snapshot if present
        key = self.snapshot_cache_key_for(app)
        snapshot = await sync_to_async(cache.get)(key)
        if snapshot:
            self._last_updated_at = int(snapshot.get("updated_at", 0))
            await self.send_json(snapshot)

    # ---- shared event handling ----
    async def _handle_update(self, event: dict) -> None:
        ts = int(event.get("updated_at", 0))
        if ts <= self._last_updated_at:
            return  # ignore stale/duplicate
        self._last_updated_at = ts
        await self.send_json({"updated_at": ts, "payload": event["payload"]})
