from bisect import bisect_right
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils.timezone import now
from sortedcontainers import SortedList

from analytics.constants import PROB_DEFAULT_CACHE_DURATION, CrashesToMonitor
from analytics.services.base import Analytics
from commons.constants import CacheKeys
from commons.logger import logger
from observers.models import Multiplier


# Probability Class
class Probability(Analytics):
    @staticmethod
    def _purge_cache_keys_for_worker(cache_key_template: str, worker_id: str) -> None:
        """Helper method to generate and delete cache keys for a specific worker in bulk."""
        crash_list = CrashesToMonitor.list()
        cache_keys = [
            cache_key_template.format(worker_id, crash) for crash in crash_list
        ]

        logger.info(f"Purging {len(cache_keys)} cache keys for worker_id={worker_id}.")
        cache.delete_many(cache_keys)

    @staticmethod
    def purge_crash_intervals_cache_for_worker(worker_id: str) -> None:
        """Delete crash intervals for a specific worker saved in cache."""
        Probability._purge_cache_keys_for_worker(
            CacheKeys.WORKER_ID_CRASH_INTERVALS,
            worker_id,
        )

    @staticmethod
    def purge_crash_query_cache_for_worker(worker_id: str) -> None:
        """Delete crash queries for a specific worker saved in cache."""
        Probability._purge_cache_keys_for_worker(
            CacheKeys.WORKER_ID_CRASH_QUERY,
            worker_id,
        )

    @staticmethod
    def fetch_gte_crashes(worker_id: str, crash: float) -> list[datetime]:
        """Fetch crashes from the database or cache in ascending order (crucial when calculating intervals)."""
        cache_key = CacheKeys.WORKER_ID_CRASH_QUERY.format(worker_id, crash)

        def fallback():
            three_days_ago = now() - timedelta(days=3)
            crashes = list(
                Multiplier.objects.filter(
                    crash__gte=crash,
                    worker__id=worker_id,
                    created_at__gte=three_days_ago,
                )
                .order_by("created_at")
                .values_list("created_at", flat=True),  # Ascending order
            )
            return crashes

        return Analytics.get_cached_data(
            cache_key=cache_key,
            fallback_fn=fallback,
            timeout=PROB_DEFAULT_CACHE_DURATION,
        )

    @staticmethod
    def time_since_last_crash(worker_id: str, crash: float) -> float:
        """Fetch the time (in seconds) since the last crash meeting or exceeding the threshold.
        This function should not be cached. We need the accurate time always
        """
        last_crash_time = (
            Multiplier.objects.filter(worker__id=worker_id, crash__gte=crash)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )  # Descending order

        if last_crash_time is None:
            return float("inf")  # No crash >= threshold found

        seconds = (now() - last_crash_time).total_seconds()
        return seconds

    @staticmethod
    def get_intervals_from_cache(worker_id: str, crash: float) -> SortedList:
        """Fetch or compute crash intervals."""

        def fallback():
            crashes = Probability.fetch_gte_crashes(worker_id, crash)
            if len(crashes) < 2:
                return SortedList()
            return SortedList(
                round((crashes[i] - crashes[i - 1]).total_seconds())
                for i in range(1, len(crashes))
            )

        cache_key = CacheKeys.WORKER_ID_CRASH_INTERVALS.format(worker_id, crash)
        return Analytics.get_cached_data(
            cache_key,
            fallback_fn=fallback,
            timeout=PROB_DEFAULT_CACHE_DURATION,
        )

    @staticmethod
    def calculate_probability(worker_id: str, crash: float) -> float:
        """Calculate probability for the given metric."""
        count = Probability.time_since_last_crash(worker_id, crash)
        intervals = Probability.get_intervals_from_cache(worker_id, crash)

        if count == float("inf") or len(intervals) == 0:
            logger.info(
                f"No qualifying crash found. Returning 0 probability for worker_id={worker_id}, crash={crash}.",
            )
            return 0.0

        position = bisect_right(intervals, count)
        probability = round((position / len(intervals)) * 100, 2)
        logger.info(
            f"Calculated probability: {probability}% for worker_id={worker_id}, crash={crash}.",
        )
        return probability
