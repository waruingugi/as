from unittest.mock import patch

from django.test import TestCase

from analytics.constants import CrashesToMonitor
from analytics.utils import format_worker_probabilities
from commons.constants import BettingApps, SeedNames
from workers.models import Worker


class TestFormatWorkerProbabilities(TestCase):
    def setUp(self) -> None:
        # Create a mock worker
        self.worker = Worker.objects.create(
            app=BettingApps.BETIKA.value, name=SeedNames.SEED_00.value
        )

    @patch("analytics.services.Probability.calculate_probability")
    def test_format_worker_probabilities(self, mock_calculate_probability) -> None:
        # Mock the return value of the probability calculation
        mock_calculate_probability.side_effect = [0.15]  # Mock values for over_20x

        # Call the function
        result = format_worker_probabilities(self.worker)

        # Expected result
        expected_probabilities = {
            "over_20x": {
                "probability": 0.15,
                "suggestion": "",
            },
        }

        expected_result = {
            "id": self.worker.id,
            "name": self.worker.name,
            "probability": expected_probabilities,
        }

        # Assert the result matches the expected output
        self.assertEqual(result, expected_result)

        # Assert the probability calculation was called with the correct arguments
        mock_calculate_probability.assert_any_call(
            self.worker.id, CrashesToMonitor.OVER_20X.value
        )
        self.assertEqual(mock_calculate_probability.call_count, len(CrashesToMonitor))
