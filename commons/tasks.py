from celery import shared_task

from commons.constants import (
    SMSProvider,
)
from commons.logger import logger
from commons.utils import UserSignalSettingsCacheManager, send_push_notification
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
def send_push_task(
    *,
    notification_type: str,
    title: str,
    message: str,
    user_ids: list[str],
    app_url: str = None,
) -> None:
    send_push_notification(
        notification_type=notification_type,
        title=title,
        message=message,
        user_ids=user_ids,
        app_url=app_url,
    )


@shared_task
def refresh_users_signal_settings():
    """
    Update users signal settings.
    This task ensures that the signal settings cache for all users is up to date.
    """
    logger.info("Refreshing users signal settings in cache...")
    UserSignalSettingsCacheManager.reload_cache()
    logger.info("Users signal settings refreshed successfully.")
