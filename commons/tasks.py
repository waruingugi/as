from celery import shared_task

from commons.constants import NotificationType, SMSProvider
from notifications.base import Notification


@shared_task
def send_sms_task(
    phone_number: str,
    message: str,
    provider=SMSProvider.HostPinnacle.value,
    type: str = NotificationType.MARKETING.value,
):
    """Background task for sending SMS using Notification."""
    Notification.send_sms(phone_number, message, provider, type)
