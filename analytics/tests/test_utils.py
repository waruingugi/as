from datetime import datetime, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from sortedcontainers import SortedList

from analytics.constants import CrashesToMonitor
from analytics.utils import cache_crash_intervals
from commons.constants import BettingApps, CacheKeys, SeedNames
from observers.models import Multiplier
from workers.models import Worker


class TestCacheCrashIntervals(TestCase):
    def setUp(self):
        # Create a worker instance
        self.worker = Worker.objects.create(
            app=BettingApps.BETIKA.value, name=SeedNames.SEED_00.value
        )

    @patch("django.utils.timezone.now")
    def test_cache_crash_intervals(self, mock_now):
        # Mock the current time
        mock_now.return_value = datetime(2025, 1, 25, 12, 0, 0)

        # Create test data for Multipliers
        Multiplier.objects.create(
            crash=25.0,
            created_at=mock_now.return_value - timedelta(days=2),
            worker=self.worker,
        )
        Multiplier.objects.create(
            crash=30.0,
            created_at=mock_now.return_value - timedelta(days=1),
            worker=self.worker,
        )
        Multiplier.objects.create(
            crash=35.0, created_at=mock_now.return_value, worker=self.worker
        )

        # Call the cache_crash_intervals function
        cache_crash_intervals()

        # Check if intervals are cached for each crash threshold in CrashesToMonitor
        for crash in CrashesToMonitor.list():
            cache_key = CacheKeys.CRASH_INTERVALS.format(crash)
            cached_intervals = cache.get(cache_key)

            # Assert the cached intervals are a SortedList
            self.assertIsInstance(cached_intervals, SortedList)

            # Recalculate intervals for validation
            three_days_ago = mock_now.return_value - timedelta(days=3)
            crashes = list(
                Multiplier.objects.filter(
                    crash__gte=crash, created_at__gte=three_days_ago
                )
                .order_by("created_at")
                .values_list("created_at", flat=True)
            )
            expected_intervals = [
                (crashes[i] - crashes[i - 1]).total_seconds()
                for i in range(1, len(crashes))
            ]

            # Assert the cached intervals match the expected intervals
            self.assertEqual(list(cached_intervals), sorted(expected_intervals))

            # Assert the cached intervals are correctly ordered
            self.assertEqual(cached_intervals, SortedList(expected_intervals))
