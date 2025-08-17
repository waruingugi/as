from enum import Enum

from django.contrib.auth import get_user_model

from notifications.push import OneSignal
from notifications.sms import HostPinnacleSMS

# Model Constants
User = get_user_model()

# LENGTH OF WORKER API KEYS
WORKER_API_KEY_LEN: int = 32


# Default cache duration
DEFAULT_CACHE_DURATION: int = 300  # 5 minutes


# PAGE SIZE
PAGE_SIZE: int = 50
MULTIPLIER_PAGE_SIZE: int = 200


class BettingApp(str, Enum):
    """Apps tracked by the API"""

    BETIKA = "BETIKA"
    # BETGR8 = "BETGR8"
    # ODIBETS = "ODIBETS"

    @staticmethod
    def list():
        return [app.value for app in BettingApp]

    @staticmethod
    def choices():
        return [(app.value, app.value) for app in BettingApp]


class SubscriptionType(str, Enum):
    """Payment Subscription Types"""

    PRO = "PRO"

    @staticmethod
    def list():
        return [sub.value for sub in SubscriptionType]

    @staticmethod
    def choices():
        return [(sub.value, sub.value) for sub in SubscriptionType]


class CacheKeys:
    """Central repository of cache keys."""

    WORKER_KEY = "worker_key:{}"
    WORKER_IS_HEALTHY = "worker_id:{}:is_healthy"
    REBOOTED_WORKER = "rebooted_worker:{}"
    WORKER_GTE_CRASH_QUERY = "worker_id:{}:over{}x:query"
    WORKER_ID_CRASH_INTERVALS = "worker_id:{}:over{}x:intervals"
    WORKER_LAST_CRASH_TIME = "worker_id:{}:time_since:{}x:"
    WORKER_CRASH_QUERY = "worker_id:{}:query"
    WORKER_PROBABILITY_SUGGESTION = "worker_id:{}:over{}:suggestion"

    USERS_SIGNAL_SETTINGS = "users_signal_settings"
    TRIGGER_SIGNAL_FLAGS = "trigger_signal_flags"
    SEED_TO_ROOM_MAPPING = "{}:{}"  # Map app seed to room number

    SIGNAL_RECORD = (
        "worker_id:{}:signal_record"  # Store signal records for a specific worker
    )


class SeedName(str, Enum):
    """Seed name options."""

    SEED_00 = "Seed 00"
    SEED_01 = "Seed 01"
    SEED_O2 = "Seed 02"

    @staticmethod
    def list():
        return [seed.value for seed in SeedName]

    @staticmethod
    def choices():
        return [(seed.value, seed.value) for seed in SeedName]


PUSH_PROVIDERS = [OneSignal]


class SMSProvider(Enum):
    """Predefined SMS providers as single instances."""

    HostPinnacle = HostPinnacleSMS  # Default provider

    @staticmethod
    def list() -> list:
        """Returns providers sorted by priority for automatic fallback handling."""
        return sorted(
            [provider.value for provider in SMSProvider], key=lambda p: p.priority
        )


class Message(str, Enum):
    OTP_SMS = "Your Rubani verification code is {}."


class PushNotification:
    class WELCOME_MESSAGE:
        title = "You now have access to Rubani!"
        message = (
            "Welcome to Rubani - the #1 aviator signals app in Kenya. "
            "Remember to activate your signals in the Settings page!"
        )


class WebSocketChannels:
    """
    WebSocket channel names for real-time updates.
    Group name must be a valid unicode string with length < 100 containing only ASCII alphanumerics,
    hyphens, underscores, or periods.
    """

    PROBABILITIES = "{}_probabilities"
    HISTORY = "{}_history"


# Websocket max lifetime in seconds
WEBSOCKET_MAX_LIFETIME_SECONDS = 60 * 15  # 15 minutes
