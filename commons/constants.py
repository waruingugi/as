from enum import Enum

from django.contrib.auth import get_user_model

# Model Constants
User = get_user_model()

# LENGTH OF WORKER API KEYS
WORKER_API_KEY_LEN: int = 32


# Default cache duration
DEFAULT_CACHE_DURATION: int = 300  # 5 minutes


# PAGE SIZE
PAGE_SIZE: int = 50


class BettingApp(str, Enum):
    """Apps tracked by the API"""

    BETIKA = "BETIKA"

    @staticmethod
    def list():
        return [app.value for app in BettingApp]

    @staticmethod
    def choices():
        return [(app.value, app.value) for app in BettingApp]


class SubscriptionType(str, Enum):
    """Payment Subscription Types"""

    BASIC = "BASIC"
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
    REBOOTED_WORKER = "rebooted_worker:{}"
    WORKER_GTE_CRASH_QUERY = "worker_id:{}:over{}x:query"
    WORKER_ID_CRASH_INTERVALS = "worker_id:{}:over{}x:intervals"
    WORKER_LAST_CRASH_TIME = "worker_id:{}:time_since:{}x:"
    WORKER_CRASH_QUERY = "worker_id:{}:query"


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
