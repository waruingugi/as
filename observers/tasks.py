import time

from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer
from django.core.cache import cache
from django_redis import get_redis_connection
from redis.exceptions import LockError

from analytics.serializers import WorkerProbabilitySerializer
from analytics.services.probability import Probability
from analytics.utils import format_worker_probabilities
from commons.constants import CacheKeys, WebSocketChannels
from commons.logger import logger
from observers.models import Multiplier
from observers.serializers import StrategySerializer, WorkerHistorySerializer
from observers.services import signal_service_engine
from observers.utils import (
    get_strategy_data,
    get_workers_crash_history,
    refresh_worker_crash_query,
)
from workers.models import Worker


@shared_task
def trigger_computations_task(multiplier_ids: list) -> None:
    """
    Trigger computations:
    - Update probabilities for seeds
    - Update payout history
    """
    logger.info("Triggering recomputations...")

    # Fetch instances from DB
    instances = Multiplier.objects.filter(id__in=multiplier_ids)

    # Update probabilities for seeds
    Probability.recompute_time_since_last_crash(instances)

    # Refresh payout history for specific worker ids
    refresh_worker_crash_query(instances)


@shared_task
def execute_signal_engine_task(multiplier_id: str) -> dict | None:
    """
    Execute the signal engine task for a specific Multiplier instance.
    This function processes the latest payout and returns the signal record if applicable.
    """

    instance = Multiplier.objects.get(id=multiplier_id)
    signal_service_engine(instance)


@shared_task
def broadcast_history_task(app: str) -> None:
    """Push the latest history to all connected websocket clients for the given app."""

    # Generate cache keys and group name for the app
    lock_key = CacheKeys.APP_HISTORY_LOCK_KEY.format(app)
    snapshot_key = CacheKeys.APP_HISTORY_SNAPSHOT.format(app)
    group_name = WebSocketChannels.HISTORY.format(app)

    # Lock and cache timeouts (in seconds)
    LOCK_TTL_SECONDS = 5  # noqa
    SNAPSHOT_TTL_SECONDS = 5 * 60  # noqa
    BLOCKING_TIMEOUT_SECONDS = 1  # noqa

    conn = get_redis_connection("default")
    try:
        # Acquire a Redis lock to prevent concurrent updates
        with conn.lock(
            lock_key,
            timeout=LOCK_TTL_SECONDS,
            blocking_timeout=BLOCKING_TIMEOUT_SECONDS,
        ):
            # Recompute and fetch the latest crash history
            payload_raw = get_workers_crash_history(app=app, recompute=True)

            # Serialize to safe types (UUID→str, datetime→ISO string, Decimal→str by default)
            payload = WorkerHistorySerializer(payload_raw, many=True).data

            updated_at = time.time_ns() // 1_000_000  # Current time in ms
            snapshot = {"updated_at": updated_at, "payload": payload}

            # Cache the snapshot for quick access
            cache.set(snapshot_key, snapshot, timeout=SNAPSHOT_TTL_SECONDS)

            # Broadcast the update to all connected websocket clients
            layer = get_channel_layer()
            async_to_sync(layer.group_send)(
                group_name,
                {
                    "type": "history.update",
                    "updated_at": updated_at,
                    "payload": payload,
                },
            )
    except LockError:
        # Another worker is already computing/broadcasting; skip this run.
        return


@shared_task
def broadcast_strategies_task(app_name: str) -> None:
    """
    Compute strategy snapshot once, serialize to safe primitives, cache it,
    and broadcast to the STRATEGY group for this app.
    """
    logger.info("Broadcasting strategies...")

    lock_key = CacheKeys.APP_STRATEGY_LOCK_KEY.format(app_name)
    snapshot_key = CacheKeys.APP_STRATEGY_SNAPSHOT.format(app_name)
    group_name = WebSocketChannels.STRATEGY.format(app_name)

    # Timeouts (match history task)
    LOCK_TTL_SECONDS = 5  # noqa

    # Strategy data is less frequent, so we can cache longer
    SNAPSHOT_TTL_SECONDS = 60 * 60 * 24  # noqa
    BLOCKING_TIMEOUT_SECONDS = 1  # noqa

    conn = get_redis_connection("default")
    try:
        # Prevent concurrent recomputes
        with conn.lock(
            lock_key,
            timeout=LOCK_TTL_SECONDS,
            blocking_timeout=BLOCKING_TIMEOUT_SECONDS,
        ):
            # 1) Recompute once
            payload_raw = get_strategy_data(app=app_name)

            # 2) Serialize to msgpack/JSON-safe types
            payload = StrategySerializer(instance=payload_raw, many=True).data

            # 3) Snapshot for new connections
            updated_at = time.time_ns() // 1_000_000  # ms
            snapshot = {"updated_at": updated_at, "payload": payload}
            cache.set(snapshot_key, snapshot, timeout=SNAPSHOT_TTL_SECONDS)

            # 4) Broadcast to all connected clients
            layer = get_channel_layer()
            async_to_sync(layer.group_send)(
                group_name,
                {
                    "type": "strategy.update",  # handled by `strategy_update` in your consumer
                    "updated_at": updated_at,
                    "payload": payload,
                },
            )
    except LockError:
        # Another worker is already doing it; skip this run.
        return


@shared_task
def broadcast_probability_task(app_name: str) -> None:
    """
    Compute probabilities once, serialize to safe primitives, cache a snapshot,
    and broadcast to the PROBABILITIES group for this app.
    """

    # Keys & group
    lock_key = CacheKeys.APP_PROBABILITY_LOCK_KEY.format(app_name)
    snapshot_key = CacheKeys.APP_PROBABILITY_SNAPSHOT.format(app_name)
    group_name = WebSocketChannels.PROBABILITIES.format(app_name)

    # Timeouts (aligned with your other tasks)
    LOCK_TTL_SECONDS = 5  # noqa
    SNAPSHOT_TTL_SECONDS = 5 * 60  # noqa
    BLOCKING_TIMEOUT_SECONDS = 1  # noqa

    conn = get_redis_connection("default")
    try:
        # Prevent concurrent recomputes
        with conn.lock(
            lock_key,
            timeout=LOCK_TTL_SECONDS,
            blocking_timeout=BLOCKING_TIMEOUT_SECONDS,
        ):
            # 1) Gather and compute
            workers = list(Worker.objects.filter(app=app_name))
            response_data = [format_worker_probabilities(w) for w in workers]

            # 2) Serialize to msgpack/JSON-safe types
            payload = WorkerProbabilitySerializer(
                instance=response_data, many=True
            ).data

            # 3) Snapshot for new connections
            updated_at = time.time_ns() // 1_000_000  # ms
            snapshot = {"updated_at": updated_at, "payload": payload}
            cache.set(snapshot_key, snapshot, timeout=SNAPSHOT_TTL_SECONDS)

            # 4) Broadcast to all connected clients
            layer = get_channel_layer()
            async_to_sync(layer.group_send)(
                group_name,
                {
                    "type": "probability.update",  # handled by `probability_update` in your consumer
                    "updated_at": updated_at,
                    "payload": payload,
                },
            )
    except LockError:
        # Another worker is already doing it; skip this run.
        return
