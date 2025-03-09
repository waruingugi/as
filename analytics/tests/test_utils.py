from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from analytics.constants import CrashesToMonitor
from analytics.utils import format_worker_probabilities, get_over_20x_suggestion
from commons.constants import BettingApp, CacheKeys, SeedName
from workers.models import Worker


class TestFormatWorkerProbabilities(TestCase):
    def setUp(self) -> None:
        # Create a mock worker
        self.worker = Worker.objects.create(
            app=BettingApp.BETIKA.value, name=SeedName.SEED_00.value
        )

    @patch("analytics.services.Probability.calculate_probability")
    def test_format_worker_probabilities(self, mock_calculate_probability) -> None:
        # Mock the return value of the probability calculation
        mock_calculate_probability.side_effect = [0.15]  # Mock values for over_20x

        # Call the function
        result = format_worker_probabilities(self.worker)

        self.assertEqual(str(result["id"]), str(self.worker.id))
        self.assertEqual(result["name"], self.worker.name)

        self.assertIn("suggestion", result["probability"]["over_20x"])
        self.assertIn("probability", result["probability"]["over_20x"])
        self.assertIn("over_20x", result["probability"])

        # Assert the probability calculation was called with the correct arguments
        mock_calculate_probability.assert_any_call(
            self.worker.id, CrashesToMonitor.OVER_20X.value
        )
        self.assertEqual(mock_calculate_probability.call_count, len(CrashesToMonitor))


class TestGetOver20xSuggestion(TestCase):
    def setUp(self) -> None:
        self.worker_a = Worker.objects.create(
            app=BettingApp.BETIKA.value, name=SeedName.SEED_00.value
        )
        self.worker_b = Worker.objects.create(
            app=BettingApp.BETIKA.value, name=SeedName.SEED_01.value
        )

    def tearDown(self) -> None:
        # Clear the cache after each test
        cache.clear()

    def test_suggestion_returned_for_probability_range(self) -> None:
        """Assert a suggestion is returned and saved to cache"""
        probability = 5.11  # A low probability
        suggestion = get_over_20x_suggestion(str(self.worker_a.id), probability)

        self.assertIsNotNone(suggestion)
        self.assertIsInstance(suggestion, str)

        cache_key = CacheKeys.WORKER_PROBABILITY_SUGGESTION.format(
            self.worker_a.id, "LOW"
        )
        cached_suggestion = cache.get(cache_key)
        self.assertIsNotNone(cached_suggestion)
        self.assertEqual(cached_suggestion["suggestion"], suggestion)

    @patch("analytics.utils.random.choice")
    def test_same_suggestion_within_same_range(self, mock_random_choice) -> None:
        """Assert the same suggestion is returned for the same probability range"""
        mock_random_choice.return_value = "Suggestion A"
        suggestion1 = get_over_20x_suggestion(str(self.worker_a.id), 80.0)
        suggestion2 = get_over_20x_suggestion(str(self.worker_a.id), 76.0)
        self.assertEqual(suggestion1, suggestion2)

    def test_new_suggestion_for_different_range(self) -> None:
        """Assert a new suggestion is returned for a different probability range"""
        suggestion1 = get_over_20x_suggestion(str(self.worker_a.id), 80.0)
        suggestion2 = get_over_20x_suggestion(str(self.worker_a.id), 30.0)
        self.assertNotEqual(suggestion1, suggestion2)

    def test_different_suggestions_for_different_workers(self) -> None:
        """Assert different suggestions are returned for different workers"""
        suggestion_a = get_over_20x_suggestion(str(self.worker_a.id), 55.0)
        suggestion_b = get_over_20x_suggestion(str(self.worker_b.id), 20.0)
        self.assertNotEqual(suggestion_a, suggestion_b)
