from hashlib import md5, sha256
from uuid import uuid4

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache

from commons.constants import SIGNAL_NOTIFICATION_TRIGGERS, BettingApp, CacheKeys
from commons.mixins import AsyncWebSocketAuthMixin
from users.models import SignalSetting


def md5_hash(value: str) -> str:
    """Convert string value into hash"""
    return md5(value.encode()).hexdigest()


def generate_uuid() -> str:
    return uuid4().hex


def generate_hash(value: str) -> str:
    hash_obj = sha256(value.encode())
    return hash_obj.hexdigest()


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
        self._remove_previous_preferences()
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
            trigger = data.get("trigger")
            if (
                app not in self.betting_apps
                or not data.get("subscribed")
                or trigger not in SIGNAL_NOTIFICATION_TRIGGERS
            ):
                self.users_signal_prefs.get(app, {}).get(trigger, set()).discard(
                    str(self.instance.user_id)
                )

    def _remove_previous_preferences(self) -> None:
        """
        Remove user from all triggers for all apps in the cache where the user has subscribed to.
        """
        for app, triggers in self.users_signal_prefs.items():
            for trigger_set in triggers.values():
                trigger_set.discard(str(self.instance.user_id))

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
                    str(self.instance.user_id)
                )

    def _save_cache(self) -> None:
        """
        Save the updated cache.
        """
        cache.set(
            CacheKeys.USERS_SIGNAL_SETTINGS,
            self.users_signal_prefs,
            timeout=self.CACHE_TIMEOUT,
        )


#
# def get_authorization_header_from_scope(scope) -> str:
#     headers = dict(scope["headers"])
#     if b"authorization" not in headers:
#         raise AuthenticationFailed("No authorization header")
#     return headers[b"authorization"].decode("utf-8")
#
# def authenticate_user_from_scope(scope):
#     auth_header = get_authorization_header_from_scope(scope)
#     jwt_auth = JWTAuthentication()
#
#     # Emulate DRF request object with META headers
#     request = type("Request", (), {"META": {"HTTP_AUTHORIZATION": auth_header}})
#     user_auth_tuple = jwt_auth.authenticate(request)
#
#     if user_auth_tuple is None:
#         raise AuthenticationFailed("Invalid token")
#
#     return user_auth_tuple[0]


class AuthJsonWebsocketConsumer(AsyncWebSocketAuthMixin, AsyncJsonWebsocketConsumer):
    async def authenticate(self) -> bool:
        try:
            self.scope["user"] = await self.authenticate_user()
        except Exception:
            await self.close()
            return False
        return True
