from asgiref.sync import async_to_sync
from celery import shared_task
from channels.layers import get_channel_layer

from analytics.services.probability import Probability
from commons.constants import WebSocketChannels
from commons.logger import logger
from observers.models import Multiplier
from observers.services import signal_service_engine
from observers.utils import (
    refresh_worker_crash_query,
)


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
def broadcast_probability_task(app_name: str) -> None:
    """
    Update WebSocket channels for the given app.
    This function can be used to notify connected clients about updates.
    """

    channel_layer = get_channel_layer()

    # Notify the probabilities group
    async_to_sync(channel_layer.group_send)(
        WebSocketChannels.PROBABILITIES.format(app_name),
        {
            "type": "probability.update",  # Calls `probability_update` in consumer
        },
    )


@shared_task
def broadcast_history_task(app_name: str) -> None:
    """
    Update WebSocket channels for the given app's history.
    This function can be used to notify connected clients about updates.
    """

    channel_layer = get_channel_layer()

    # Notify the history group
    async_to_sync(channel_layer.group_send)(
        WebSocketChannels.HISTORY.format(app_name),
        {
            "type": "history.update",  # Calls `history_update` in consumer
        },
    )


@shared_task
def execute_signal_engine_task(multiplier_id: str) -> dict | None:
    """
    Execute the signal engine task for a specific Multiplier instance.
    This function processes the latest payout and returns the signal record if applicable.
    """

    instance = Multiplier.objects.get(id=multiplier_id)
    signal_service_engine(instance)


@shared_task
def broadcast_strategies_task(app_name: str) -> None:
    """
    Update WebSocket channels for the given app's strategy.
    This function can be used to notify connected clients about updates.
    """

    channel_layer = get_channel_layer()

    # Notify the predictions group
    async_to_sync(channel_layer.group_send)(
        WebSocketChannels.STRATEGY.format(app_name),
        {
            "type": "strategy.update",  # Calls `strategy_update` in consumer
        },
    )
