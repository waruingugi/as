from django.core.cache import cache

from commons.constants import SIGNAL_NOTIFICATION_TRIGGERS, BettingApp, CacheKeys


def default_signal_preference() -> dict:
    """Generate the default signal preference for a user in the SignalSettings model."""
    default_preference = {}
    for app in BettingApp.list():
        default_preference[app] = {
            "subscribed": False,
            "trigger": None,
        }
    return default_preference


class UserSignalSettingsCacheManager:
    """
    Class to handle updating the users_signal_prefs cache.
    """

    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

    def __init__(self, instance) -> None:
        self.instance = instance
        self.betting_apps = set(BettingApp.list())
        self.users_signal_prefs = cache.get(CacheKeys.USERS_SIGNAL_SETTINGS, {})

    @classmethod
    def update(cls, instance):
        """
        Classmethod entry-point so you can call:
            UserSignalSettingsCacheManager.update(instance)
        """
        return cls(instance)._execute()

    def _execute(self) -> None:
        """
        Update the users_signal_prefs cache.
        """
        # Remove invalid or unsubscribed preferences
        self._remove_invalid_preferences()

        # Add or update valid preferences
        self._add_valid_preferences()

        # Save updated cache
        cache.set(
            CacheKeys.USERS_SIGNAL_SETTINGS,
            self.users_signal_prefs,
            timeout=self.CACHE_TIMEOUT,
        )

    def _remove_invalid_preferences(self) -> None:
        """
        Remove user from cache if unsubscribed or invalid trigger.
        """
        for app, data in self.instance.preference.items():
            if (
                app not in self.betting_apps
                or not data.get("subscribed")
                or data.get("trigger") not in SIGNAL_NOTIFICATION_TRIGGERS
            ):
                if (
                    app in self.users_signal_prefs
                    and data.get("trigger") in self.users_signal_prefs[app]
                ):
                    self.users_signal_prefs[app][data["trigger"]].discard(
                        self.instance.user_id
                    )

    def _add_valid_preferences(self) -> None:
        """
        Add or update user in cache for valid preferences.
        """
        for app, data in self.instance.preference.items():
            if (
                app in self.betting_apps
                and data.get("subscribed")
                and data.get("trigger") in SIGNAL_NOTIFICATION_TRIGGERS
            ):
                self.users_signal_prefs.setdefault(app, {})
                self.users_signal_prefs[app].setdefault(data["trigger"], set()).add(
                    self.instance.user_id
                )
