from datetime import datetime, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils.timezone import now
from sortedcontainers import SortedList

from analytics.services.probability import Probability


class TestProbability(TestCase):
    def setUp(self):
        self.worker_id = "test_worker_id"
        self.crash_threshold = 20.0

    def tearDown(self):
        cache.clear()

    @patch("analytics.services.base.cache.get")  # Mock the cache directly
    @patch("analytics.services.probability.Multiplier.objects.filter")
    @patch(
        "analytics.services.base.cache.set"
    )  # Mock cache.set to avoid actual cache writes
    def test_fetch_crashes_from_cache(
        self, mock_cache_set, mock_filter, mock_cache_get
    ):
        """Test fetching crashes from cache or database."""
        # Mock cache hit
        mock_cache_get.return_value = [
            now() - timedelta(days=2),
            now() - timedelta(days=1),
            now(),
        ]

        crashes = Probability.fetch_crashes(self.worker_id, self.crash_threshold)
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

        crashes = Probability.fetch_crashes(self.worker_id, self.crash_threshold)
        mock_cache_get.assert_called_once()
        mock_filter.assert_called_once()
        mock_cache_set.assert_called_once()  # Ensure fallback result was cached
        self.assertEqual(len(crashes), 3)

    @patch("analytics.services.base.cache.get")  # Mock the cache directly
    @patch("analytics.services.probability.Multiplier.objects.filter")
    @patch(
        "analytics.services.base.cache.set"
    )  # Mock cache.set to avoid actual cache writes
    def test_time_since_last_crash(self, mock_cache_set, mock_filter, mock_cache_get):
        """Test calculating time since the last crash."""
        # Mock cache hit
        mock_cache_get.return_value = 3600.0

        seconds = Probability.time_since_last_crash(
            self.worker_id, self.crash_threshold
        )
        mock_cache_get.assert_called_once()
        self.assertEqual(seconds, 3600.0)

        # Mock cache miss
        mock_cache_get.reset_mock()
        mock_cache_get.return_value = None  # Simulate cache miss
        # mock_filter.return_value.order_by.return_value.values_list.return_value.first.return_value = (
        #     now() - timedelta(hours=1)
        # )

        seconds = Probability.time_since_last_crash(
            self.worker_id, self.crash_threshold
        )
        mock_cache_get.assert_called_once()
        mock_filter.assert_called_once()
        mock_cache_set.assert_called_once()  # Ensure fallback result was cached
        self.assertTrue(seconds > 0)

    @patch("analytics.services.base.cache.get")  # Mock the cache directly
    @patch("analytics.services.probability.Probability.fetch_crashes")
    @patch(
        "analytics.services.base.cache.set"
    )  # Mock cache.set to avoid actual cache writes
    def test_get_intervals_from_cache(
        self, mock_cache_set, mock_fetch_crashes, mock_cache_get
    ):
        """Test fetching or calculating intervals from cache."""
        # Mock cache hit
        mock_cache_get.return_value = SortedList([100.0, 200.0, 300.0])

        intervals = Probability.get_intervals_from_cache(
            self.worker_id, self.crash_threshold
        )
        mock_cache_get.assert_called_once()
        self.assertEqual(intervals, SortedList([100.0, 200.0, 300.0]))

        # Mock cache miss
        mock_cache_get.reset_mock()
        mock_cache_get.return_value = None  # Simulate cache miss
        mock_fetch_crashes.return_value = [
            now() - timedelta(seconds=300),
            now() - timedelta(seconds=200),
            now() - timedelta(seconds=100),
            now(),
        ]

        intervals = Probability.get_intervals_from_cache(
            self.worker_id, self.crash_threshold
        )
        mock_fetch_crashes.assert_called_once_with(self.worker_id, self.crash_threshold)
        mock_cache_set.assert_called_once()  # Ensure fallback result was cached
        self.assertEqual(
            intervals, SortedList([100, 100, 100])
        )  # Rounded to full seconds

    @patch("analytics.services.probability.Probability.time_since_last_crash")
    @patch("analytics.services.probability.Probability.get_intervals_from_cache")
    def test_calculate_probability(
        self, mock_get_intervals, mock_time_since_last_crash
    ):
        """Test calculating probability based on crashes and intervals."""
        # Mock data
        mock_time_since_last_crash.return_value = 150
        mock_get_intervals.return_value = SortedList([100, 200, 300])  # Full seconds

        probability = Probability.calculate_probability(
            self.worker_id, self.crash_threshold
        )
        mock_time_since_last_crash.assert_called_once()
        mock_get_intervals.assert_called_once()
        self.assertEqual(probability, 33.33)

        # Test no intervals
        mock_get_intervals.return_value = SortedList()

        probability = Probability.calculate_probability(
            self.worker_id, self.crash_threshold
        )
        self.assertEqual(probability, 0.0)

        # Test no crashes meeting the threshold
        mock_time_since_last_crash.return_value = float("inf")

        probability = Probability.calculate_probability(
            self.worker_id, self.crash_threshold
        )
        self.assertEqual(probability, 0.0)
