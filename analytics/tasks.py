from celery import shared_task

from commons.logger import logger


@shared_task
def recalculate_crash_intervals() -> None:
    logger.info("Starting task to recalculate crash intervals...")
    pass
