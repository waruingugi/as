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
