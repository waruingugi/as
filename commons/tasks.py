from collections import defaultdict

from celery import shared_task
from django.core.cache import cache

from commons.constants import (
    PUSH_PROVIDERS,
    SIGNAL_NOTIFICATION_TRIGGERS,
    BettingApp,
    CacheKeys,
    SMSProvider,
)
from commons.logger import logger
from notifications.base import Notification
from notifications.constants import NotificationType
from users.models import SignalSetting


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


@shared_task
def refresh_users_signal_settings():
    """
    Update users signal settings.
    This task ensures that the signal settings for all users are up to date.
    It is called periodically.
    """
    logger.info("Refreshing users signal settings in cache...")

    betting_apps = set(BettingApp.list())
    users_signal_prefs = defaultdict(lambda: defaultdict(set))
    all_signal_settings = SignalSetting.objects.select_related("user").only(
        "preference", "user__id"
    )

    for signal_setting in all_signal_settings:
        user_preferences = {
            app: data
            for app, data in signal_setting.preference.items()
            if app in betting_apps  # App is valid
            and data.get("subscribed")  # Subscribed is True
            and data.get("trigger") in SIGNAL_NOTIFICATION_TRIGGERS  # Is valid trigger
        }

        # Update preferences only if invalid apps or triggers were removed
        if user_preferences != signal_setting.preference:
            signal_setting.preference = user_preferences
            signal_setting.save(update_fields=["preference"])

        # Process valid preferences
        for app_name, app_data in user_preferences.items():
            users_signal_prefs[app_name][app_data["trigger"]].add(
                signal_setting.user_id
            )

    # Save the updated/refreshed signal settings to cache
    cache.set(
        CacheKeys.USERS_SIGNAL_SETTINGS, users_signal_prefs, timeout=60 * 60 * 24
    )  # Cache for 24 hours
    logger.info("Users signal settings refreshed successfully.")
