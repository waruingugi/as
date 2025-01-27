from enum import Enum


class CrashesToMonitor(float, Enum):
    """Crashes used to calculate probabilities."""

    OVER_20X = 20.0
    # OVER_50X = 50.0

    @staticmethod
    def list():
        return [crash.value for crash in CrashesToMonitor]


PROB_DEFAULT_CACHE_DURATION: int = 600
