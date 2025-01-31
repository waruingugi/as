from celery import shared_task

from commons.constants import PUSH_PROVIDERS, SMSProvider
from commons.logger import logger
from notifications.base import Notification
from notifications.constants import NotificationType


@shared_task
def send_sms_task(
    *,
    phone_number: str,
    message: str,
    provider=SMSProvider.HostPinnacle.value,
    type: str = NotificationType.MARKETING.value,
):
    """Background task for sending SMS using Notification."""
    Notification.send_sms(phone_number, message, provider, type)


@shared_task  # type: ignore
def send_push_task(*, type: str, title: str, message: str, user_id: str) -> bool:
    logger.info("Sending push notification in background...")
    for provider in PUSH_PROVIDERS:
        if provider.send_push(type=type, title=title, message=message, user_id=user_id):
            return True

    # Raise error if all providers failed here
    logger.error("Failed to send push notification in the background")
    return False
