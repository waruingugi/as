from enum import Enum

from django.contrib.auth import get_user_model

# Model Constants
User = get_user_model()

# LENGTH OF WORKER API KEYS
WORKER_API_KEY_LEN: int = 32


class BettingApps(str, Enum):
    """Apps tracked by the API"""

    BETIKA = "BETIKA"

    @staticmethod
    def list():
        return [app.value for app in BettingApps]

    @staticmethod
    def choices():
        return [(app.value, app.value) for app in BettingApps]


class CacheKeys:
    """Central repository of cache keys."""

    WORKER_KEY = "worker_key:{}"
    SEED_SELECTOR = "{}_seed_selector"
    REBOOTED_WORKER = "rebooted_worker:{}"
    CRASH_INTERVALS = "{}x_crash_intervals"  # Derived from CrashesToMonitor constant


class SeedNames(str, Enum):
    """Seed name options."""

    SEED_00 = "Seed 00"
    SEED_01 = "Seed 01"
    SEED_O2 = "Seed 02"

    @staticmethod
    def list():
        return [seed.value for seed in SeedNames]

    @staticmethod
    def choices():
        return [(seed.value, seed.value) for seed in SeedNames]
