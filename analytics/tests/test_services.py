from datetime import datetime, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils.timezone import now

from analytics.constants import CrashesToMonitor
from analytics.services.probability import Probability


class TestProbability(TestCase):
    def setUp(self):
        self.worker_id = "test_worker_id"
        self.crash_threshold = CrashesToMonitor.OVER_20X.value

        self.worker_ids = ["worker1", "worker2"]
        self.crash_list = [
            CrashesToMonitor.OVER_20X.value,
            CrashesToMonitor.OVER_50X.value,
        ]

    def tearDown(self):
        cache.clear()

    @patch("analytics.services.base.cache.get")
    @patch("analytics.services.probability.Multiplier.objects.filter")
    @patch("analytics.services.base.cache.set")
    def test_fetch_gte_crashes_from_cache(
        self,
        mock_cache_set,
        mock_filter,
        mock_cache_get,
    ) -> None:
        """Test fetching crashes from cache or database."""
        # Mock cache hit
        mock_cache_get.return_value = [
            now() - timedelta(days=2),
            now() - timedelta(days=1),
            now(),
        ]

        crashes = Probability.fetch_gte_crashes(self.worker_id, self.crash_threshold)
        mock_cache_get.assert_called_once()
        self.assertEqual(len(crashes), 3)
        self.assertTrue(all(isinstance(c, datetime) for c in crashes))

        # Mock cache miss
        mock_cache_get.reset_mock()
        mock_cache_get.return_value = None  # Simulate cache miss
        mock_filter.return_value.order_by.return_value.values_list.return_value = [
            now() - timedelta(days=2),
            now() - timedelta(days=1),
            now(),
        ]

        crashes = Probability.fetch_gte_crashes(self.worker_id, self.crash_threshold)
        mock_cache_get.assert_called_once()
        mock_filter.assert_called_once()
        mock_cache_set.assert_called_once()  # Ensure fallback result was cached
        self.assertEqual(len(crashes), 3)
