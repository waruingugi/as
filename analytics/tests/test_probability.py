from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase
from django.utils.timezone import now
from sortedcontainers import SortedList

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

    # Black will ignore this function
    # fmt: off
    @patch("analytics.services.base.cache.get")
    @patch("analytics.services.probability.Multiplier.objects.filter")
    @patch("analytics.services.base.cache.set")
    def test_time_since_last_crash(
        self, mock_cache_set, mock_filter, mock_cache_get
    ) -> None:
        """Test calculating time since the last crash with and without recompute."""

        # Test cache hit
        mock_cache_get.return_value = 3600.0
        seconds = Probability.time_since_last_crash(
            self.worker_id, self.crash_threshold
        )
        mock_cache_get.assert_called_once()
        self.assertEqual(seconds, 3600.0)

        # Test cache miss with recompute=False
        mock_cache_get.reset_mock()
        mock_cache_get.return_value = None
        mock_filter.return_value.order_by.return_value.values_list.return_value.first.return_value = (
            now() - timedelta(hours=1)
        )

        seconds = Probability.time_since_last_crash(
            self.worker_id, self.crash_threshold
        )
        mock_cache_get.assert_called_once()
        mock_filter.assert_called_once_with(
            worker__id=self.worker_id,
            crash__gte=self.crash_threshold,
        )
        mock_cache_set.assert_called_once()  # Ensure recomputed value was cached
        self.assertTrue(0 < round(seconds) <= 3600)

        # Test recompute=True
        mock_cache_get.reset_mock()
        mock_filter.reset_mock()
        mock_cache_set.reset_mock()

        mock_filter.return_value.order_by.return_value.values_list.return_value.first.return_value = (
            now() - timedelta(hours=2)
        )

        seconds = Probability.time_since_last_crash(
            self.worker_id, self.crash_threshold, recompute=True
        )
        mock_cache_get.assert_not_called()  # Cache is bypassed
        mock_filter.assert_called_once_with(
            worker__id=self.worker_id,
            crash__gte=self.crash_threshold,
        )
        mock_cache_set.assert_called_once()  # Ensure recomputed value was cached
        self.assertTrue(0 < round(seconds) <= 7200)
    # fmt: on

    @patch("analytics.services.base.cache.get")
    @patch("analytics.services.probability.Probability.fetch_gte_crashes")
    @patch("analytics.services.base.cache.set")
    def test_get_intervals_from_cache(
        self,
        mock_cache_set,
        mock_fetch_gte_crashes,
        mock_cache_get,
    ) -> None:
        """Test fetching or calculating intervals from cache."""
        # Mock cache hit
        mock_cache_get.return_value = SortedList([100.0, 200.0, 300.0])

        intervals = Probability.get_intervals_from_cache(
            self.worker_id,
            self.crash_threshold,
        )
        mock_cache_get.assert_called_once()
        self.assertEqual(intervals, SortedList([100.0, 200.0, 300.0]))

        # Mock cache miss
        mock_cache_get.reset_mock()
        mock_cache_get.return_value = None  # Simulate cache miss
        mock_fetch_gte_crashes.return_value = [
            now() - timedelta(seconds=300),
            now() - timedelta(seconds=200),
            now() - timedelta(seconds=100),
            now(),
        ]

        intervals = Probability.get_intervals_from_cache(
            self.worker_id,
            self.crash_threshold,
        )
        mock_fetch_gte_crashes.assert_called_once_with(
            self.worker_id,
            self.crash_threshold,
        )
        mock_cache_set.assert_called_once()  # Ensure fallback result was cached
        self.assertEqual(
            intervals,
            SortedList([100, 100, 100]),
        )  # Rounded to full seconds

    @patch("analytics.services.probability.Probability.time_since_last_crash")
    @patch("analytics.services.probability.Probability.get_intervals_from_cache")
    def test_calculate_probability(
        self,
        mock_get_intervals,
        mock_time_since_last_crash,
    ) -> None:
        """Test calculating probability based on crashes and intervals."""
        # Mock data
        mock_time_since_last_crash.return_value = 150
        mock_get_intervals.return_value = SortedList([100, 200, 300])  # Full seconds

        probability = Probability.calculate_probability(
            self.worker_id,
            self.crash_threshold,
        )
        mock_time_since_last_crash.assert_called_once()
        mock_get_intervals.assert_called_once()
        self.assertEqual(probability, 33.33)

        # Test no intervals
        mock_get_intervals.return_value = SortedList()

        probability = Probability.calculate_probability(
            self.worker_id,
            self.crash_threshold,
        )
        self.assertEqual(probability, 0.0)

        # Test no crashes meeting the threshold
        mock_time_since_last_crash.return_value = float("inf")

        probability = Probability.calculate_probability(
            self.worker_id,
            self.crash_threshold,
        )
        self.assertEqual(probability, 0.0)

    @patch(
        "analytics.services.probability.Probability.purge_crash_intervals_cache_for_worker",
    )
    def test_purge_crash_intervals_cache_for_worker(self, mock_purge_cache) -> None:
        """Test purging crash intervals cache for a specific worker."""
        Probability.purge_crash_intervals_cache_for_worker(self.worker_id)

        mock_purge_cache.assert_called_once_with(self.worker_id)

    @patch(
        "analytics.services.probability.Probability.purge_crash_query_cache_for_worker",
    )
    def test_purge_crash_query_cache_for_worker(self, mock_purge_cache) -> None:
        """Test purging crash query cache for a specific worker."""
        Probability.purge_crash_query_cache_for_worker(self.worker_id)

        mock_purge_cache.assert_called_once_with(self.worker_id)

    @patch("analytics.services.probability.Probability.time_since_last_crash")
    def test_recompute_time_since_last_crash(self, mock_time_since_last_crash):
        """Test recompute_time_since_last_crash for proper recomputation."""
        # Create mock Multiplier instances
        mock_instance_1 = MagicMock(worker_id="worker1")
        mock_instance_2 = MagicMock(worker_id="worker2")
        mock_instance_3 = MagicMock(worker_id="worker1")
        instances = [mock_instance_1, mock_instance_2, mock_instance_3]

        # Mock time_since_last_crash behavior
        mock_time_since_last_crash.return_value = 3600.0

        # Call the function
        Probability.recompute_time_since_last_crash(instances)

        # Ensure time_since_last_crash is called for each unique worker_id and crash threshold
        expected_calls = [
            ((worker_id, crash_threshold, True),)
            for worker_id in {"worker1", "worker2"}
            for crash_threshold in CrashesToMonitor.list()
        ]
        mock_time_since_last_crash.assert_has_calls(expected_calls, any_order=True)
        self.assertEqual(
            mock_time_since_last_crash.call_count,
            len({"worker1", "worker2"}) * len(CrashesToMonitor.list()),
        )
