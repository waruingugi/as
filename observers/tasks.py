from celery import shared_task

from analytics.services.probability import Probability
from commons.logger import logger
from observers.models import Multiplier
from observers.utils import refresh_worker_crash_query


@shared_task
def trigger_computations(multiplier_ids: list) -> None:
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
