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
