from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.dispatch import receiver

from analytics.services.probability import Probability
from observers.models import Multiplier, post_bulk_create
from observers.utils import SignalNotificationMonitor, refresh_worker_crash_query


@receiver(post_bulk_create, sender=Multiplier)
def handle_bulk_created(sender, instances, **kwargs) -> None:
    """
    Signal to handle bulk-created Multiplier instances.
    Delegates analytics-related tasks (e.g., cache updates) to the analytics app.
    """
    if not instances:
        return

    # Delegate to the analytics app
    Probability.recompute_time_since_last_crash(instances)

    # Refresh query for specific worker ids
    refresh_worker_crash_query(instances)

    # Alert the signal monitor
    SignalNotificationMonitor.process_latest_payout(
        instances[-1]
    )  # Process the latest payout

    # websocket notification to update probabilities
    # channel_layer = get_channel_layer()
    # app_name = instances[-1].worker.app  # Adjust if needed
    #
    # async_to_sync(channel_layer.group_send)(
    #     f"probabilities_{app_name}",
    #     {
    #         "type": "probability.update",  # Calls `probability_update` in consumer
    #     },
    # )
    channel_layer = get_channel_layer()
    app_name = instances[-1].worker.app  # Or the relevant app

    async_to_sync(channel_layer.group_send)(
        f"workerhistory_{app_name}",
        {
            "type": "history.update",  # This triggers `history_update` in the consumer
        },
    )
