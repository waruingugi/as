from bisect import bisect_right
from datetime import datetime, timedelta
from decimal import Decimal

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
    def recompute_time_since_last_crash(instances):
        """
        Recompute caches crash time count for worker IDs for given instances.
        """
        if not instances:
            return

        # Collect unique worker IDs from the instances
        worker_ids = {instance.worker_id for instance in instances}

        # Iterate over worker IDs and crash thresholds to recompute
        for worker_id in worker_ids:
            for crash_threshold in CrashesToMonitor.list():
                # Recompute time since last crash for each combination
                Probability.time_since_last_crash(worker_id, crash_threshold, True)

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
            CacheKeys.WORKER_GTE_CRASH_QUERY,
            worker_id,
        )

    @staticmethod
    def fetch_gte_crashes(worker_id: str, crash: float) -> list[datetime]:
        """Fetch crashes from the database or cache in ascending order (crucial when calculating intervals)."""
        cache_key = CacheKeys.WORKER_GTE_CRASH_QUERY.format(worker_id, crash)

        def fallback():
            logger.info(f"Fetching {crash}x caches for {worker_id}.")
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
    def time_since_last_crash(
        worker_id: str, crash: float, recompute: bool = False
    ) -> float:
        """
        Fetch or compute the time (in seconds) since the last crash.

        - If `recompute` is True (e.g., when called by a Django signal), recompute the value
          and update the cache.
        - If `recompute` is False, return the cached value if available. Recompute if not cached.
        """
        cache_key = CacheKeys.WORKER_LAST_CRASH_TIME.format(worker_id, crash)

        if not recompute:
            # Attempt to fetch from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

        # Recompute the time since the last crash
        logger.info(f"Recomputing seconds since {crash}x caches for {worker_id}.")
        last_crash_time = (
            Multiplier.objects.filter(worker__id=worker_id, crash__gte=crash)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )  # Descending order

        if last_crash_time is None:
            result = float("inf")  # No crash >= threshold found
        else:
            result = (now() - last_crash_time).total_seconds()

        # Update the cache
        cache.set(cache_key, result, timeout=60)
        return result

    @staticmethod
    def get_intervals_from_cache(worker_id: str, crash: float) -> SortedList:
        """Fetch or compute crash intervals."""

        def fallback():
            logger.info(f"Get {crash}x intervals for {worker_id}.")
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
    def calculate_probability(worker_id: str, crash: float) -> Decimal:
        """Calculate probability for the given metric."""
        count = Probability.time_since_last_crash(worker_id, crash)
        intervals = Probability.get_intervals_from_cache(worker_id, crash)

        if count == float("inf") or len(intervals) == 0:
            logger.info(
                f"No qualifying crash found. Returning 0 probability for worker_id={worker_id}, crash={crash}.",
            )
            return Decimal(0.0)

        position = bisect_right(intervals, count)
        probability = Decimal((position / len(intervals)) * 100)
        logger.info(
            f"Calculated probability for worker_id={worker_id}, crash={crash}.",
        )
        return probability
