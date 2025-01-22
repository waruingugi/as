from collections import defaultdict
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.utils.timezone import now, timedelta

from orchestrator.tasks import find_failing_workers, identify_similar_workers


class TestIdentifySimilarWorkersTask(TestCase):
    @patch("orchestrator.tasks.Worker.objects.filter")
    @patch("orchestrator.tasks.Multiplier.objects.filter")
    @patch("orchestrator.tasks.find_similar_workers")
    @patch("orchestrator.tasks.reboot_worker")
    def test_reboot_similar_workers_successfully(
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


class TestFindFailingWorkers(TestCase):
    @patch("orchestrator.tasks.Worker.objects.all")
    @patch("orchestrator.tasks.Multiplier.objects.filter")
    @patch("orchestrator.tasks.reboot_worker")
    def test_all_workers_are_active(
        self, mock_reboot_worker, mock_multiplier_filter, mock_worker_all
    ) -> None:
        # Mock workers
        worker = MagicMock(id=1, name="Seed 00")
        mock_worker_all.return_value = [worker]

        # Mock recent crash
        three_minutes_ago = now() - timedelta(minutes=3)

        # Mock the queryset chain with .first()
        mock_queryset = MagicMock()
        mock_queryset.order_by.return_value = mock_queryset
        mock_queryset.values_list.return_value = mock_queryset
        mock_queryset.first.return_value = three_minutes_ago
        mock_multiplier_filter.return_value = mock_queryset

        # Call the function
        find_failing_workers()

        # Assertions
        mock_reboot_worker.assert_not_called()

    @patch("orchestrator.tasks.Worker.objects.all")
    @patch("orchestrator.tasks.Multiplier.objects.filter")
    @patch("orchestrator.tasks.reboot_worker")
    def test_some_workers_are_failing(
        self, mock_reboot_worker, mock_multiplier_filter, mock_worker_all
    ) -> None:
        # Mock workers
        worker = MagicMock(id=1, name="Seed 00")
        mock_worker_all.return_value = [worker]

        # Mock crash posted an hour ago
        one_hour_ago = now() - timedelta(hours=1)

        # Mock the queryset chain with .first()
        mock_queryset = MagicMock()
        mock_queryset.order_by.return_value = mock_queryset
        mock_queryset.values_list.return_value = mock_queryset
        mock_queryset.first.return_value = one_hour_ago
        mock_multiplier_filter.return_value = mock_queryset

        # Call the function
        find_failing_workers()

        # Assertions
        mock_reboot_worker.assert_called_once_with(worker.id)
