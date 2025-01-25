from celery import shared_task

from analytics.utils import cache_crash_intervals
from commons.logger import logger


@shared_task
def recalculate_crash_intervals() -> None:
    logger.info("Starting task to recalculate crash intervals...")
    cache_crash_intervals()
