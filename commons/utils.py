from hashlib import md5, sha256
from uuid import uuid4

from django.core.cache import cache

from commons.constants import (
    PUSH_PROVIDERS,
    AppPageURL,
    BettingApp,
    CacheKeys,
    NotificationCollapseID,
)
from commons.logger import logger
from notifications.constants import NotificationChannel
from users.models import SignalSetting


def md5_hash(value: str) -> str:
    """Convert string value into hash"""
    return md5(value.encode()).hexdigest()


def generate_uuid() -> str:
    return uuid4().hex


def generate_hash(value: str) -> str:
    hash_obj = sha256(value.encode())
    return hash_obj.hexdigest()


def get_worker_health(worker_id: str) -> bool:
    """This function checks the health of a worker by looking up its health status in the cache.
    If the worker's health status is not found in the cache, it defaults to True (healthy).
    """
    cache_key = CacheKeys.WORKER_IS_HEALTHY.format(worker_id)
    return cache.get(cache_key, True)  # Default to True if not found


def get_room_name(app: str, worker_name: str) -> str:
    """Get the room name of the worker based on the app and seed."""
    cache_key = CacheKeys.SEED_TO_ROOM_MAPPING.format(app, worker_name)
    room_name = cache.get(cache_key)
    room_name = worker_name.replace("Seed", "Room") if room_name is None else room_name
    return room_name


class UserSignalSettingsCacheManager:
    """
    Class to handle updating and refreshing the users_signal_prefs cache.
    """

    CACHE_TIMEOUT = None  # infinity

    def __init__(self, instance=None) -> None:
        self.instance = instance
        self.betting_apps = set(BettingApp.list())
        self.users_signal_prefs = cache.get(CacheKeys.USERS_SIGNAL_SETTINGS, {})

    @classmethod
    def update(cls, instance):
        """
        Update the cache for a single SignalSetting instance.
        """
        return cls(instance)._execute()

    @classmethod
    def reload_cache(cls):
        """
        Refresh the entire users_signal_prefs cache using all SignalSettings.
        """
        manager = cls()
        manager.users_signal_prefs = {}  # Clear previous cache
        manager._refresh_cache()

    def _execute(self) -> None:
        """
        Update the users_signal_prefs cache for a single instance.
        """
        # self._remove_previous_preferences()
        self._remove_invalid_preferences()
        self._add_valid_preferences()
        self._save_cache()

    def _refresh_cache(self) -> None:
        """
        Refresh the entire users_signal_prefs cache using all SignalSettings.
        """

        all_signal_settings = SignalSetting.objects.select_related("user").only(
            "preference", "user__id"
        )

        for signal_setting in all_signal_settings:
            self.instance = signal_setting
            self._remove_invalid_preferences()
            self._add_valid_preferences()

        self._save_cache()

    def _remove_invalid_preferences(self) -> None:
        """
        Remove user from cache if unsubscribed or invalid trigger.
        """
        for app, data in self.instance.preference.items():
            if app not in self.betting_apps or not data.get("subscribed"):
                if app in self.users_signal_prefs:
                    self.users_signal_prefs[app].discard(str(self.instance.user_id))
                    self._send_notification(app, str(self.instance.user_id), False)

    # def _remove_previous_preferences(self) -> None:
    #     """
    #     Remove user from all triggers for all apps in the cache where the user has subscribed to.
    #     """
    #     for app in self.users_signal_prefs.values():
    #         app.discard(str(self.instance.user_id))

    def _add_valid_preferences(self) -> None:
        """
        Add or update user in cache for valid preferences.
        """
        for app, data in self.instance.preference.items():
            if app in self.betting_apps and data.get("subscribed"):
                self.users_signal_prefs.setdefault(app, set())
                self.users_signal_prefs[app].add(str(self.instance.user_id))
                self._send_notification(app, str(self.instance.user_id), True)

    def _save_cache(self) -> None:
        """
        Save the updated cache.
        """
        cache.set(
            CacheKeys.USERS_SIGNAL_SETTINGS,
            self.users_signal_prefs,
            timeout=self.CACHE_TIMEOUT,
        )

    def _send_notification(self, app: str, subscriber: str, subscribed: bool) -> None:
        """
        Send a push notification to a new user that they have successfully subscribed to the app.
        """
        logger.info(f"Sending subscription notification for {app} to {subscriber}")
        title = (
            f"You've subscribed to {app} signals!"
            if subscribed
            else f"You've unsubscribed from {app}"
        )
        message = (
            f"You'll be notified when an over 20x payout is close for {app}."
            if subscribed
            else "You will no longer receive its signals."
        )

        send_push_notification(
            notification_type=NotificationChannel.PUSH.value,
            title=title,
            message=message,
            user_ids=[subscriber],
            app_url=AppPageURL.SETTINGS.value,
            collapse_id=NotificationCollapseID.SUBSCRIPTION.format(app),
        )


def send_push_notification(
    *,
    notification_type: str,
    title: str,
    message: str,
    user_ids: list[str],
    app_url: str = None,
    collapse_id: str = None,
) -> bool:
    """Send a push notification using the configured providers."""
    logger.info("Sending push notification in background...")
    for provider in PUSH_PROVIDERS:
        if provider.send_push(
            notification_type=notification_type,
            title=title,
            message=message,
            user_ids=user_ids,
            app_url=app_url,
            collapse_id=collapse_id,
        ):
            return True

    # Raise error if all providers failed here
    logger.error("Failed to send push notification in the background")
    return False
