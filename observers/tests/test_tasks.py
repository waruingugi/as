from collections import defaultdict
from unittest.mock import MagicMock, patch

from django.test import TestCase

from observers.tasks import identify_similar_workers


class TestIdentifySimilarWorkersTask(TestCase):
    @patch("observers.tasks.Worker.objects.filter")
    @patch("observers.tasks.Multiplier.objects.filter")
    @patch("observers.tasks.find_similar_workers")
    @patch("observers.tasks.reboot_worker")
    def test_limited_recent_payouts(
        self,
        mock_reboot_worker,
        mock_find_similar,
        mock_multiplier_filter,
        mock_worker_filter,
    ) -> None:
        # Mock app and workers
        mock_worker_filter.return_value.values_list.return_value = [1, 2]
        mock_multiplier_filter.side_effect = [
            MagicMock(
                order_by=MagicMock(
                    return_value=MagicMock(
                        values_list=MagicMock(return_value=[1.0, 2.0, 3.0])
                    )
                )
            ),
            MagicMock(
                order_by=MagicMock(
                    return_value=MagicMock(
                        values_list=MagicMock(return_value=[3.0, 4.0, 5.0])
                    )
                )
            ),
        ]
        mock_find_similar.return_value = {(1, 2): 0.8}

        # Run the task
        identify_similar_workers()

        # Assertions
        expected_worker_payouts = defaultdict(
            set, {1: {1.0, 2.0, 3.0}, 2: {3.0, 4.0, 5.0}}
        )
        mock_find_similar.assert_called_once_with(expected_worker_payouts, 0.8)
        mock_reboot_worker.assert_called_once()
