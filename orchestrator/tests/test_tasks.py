from collections import defaultdict
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.utils.timezone import now, timedelta

from orchestrator.tasks import find_failing_workers, identify_similar_workers
from workers.models import Worker


class TestIdentifySimilarWorkersTask(TestCase):
    @patch("orchestrator.tasks.Worker.objects.filter")
    @patch("orchestrator.tasks.Multiplier.objects.filter")
    @patch("orchestrator.tasks.find_similar_workers")
    @patch("orchestrator.tasks.reboot_worker")
    @patch("orchestrator.tasks.BettingApp.list", return_value=["BETIKA"])
    def test_reboot_similar_workers_successfully(
        self,
        mock_app_list,
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
    @patch("orchestrator.tasks.Worker.objects.filter")
    @patch("orchestrator.tasks.Multiplier.objects.filter")
    @patch("orchestrator.tasks.reboot_worker")
    def test_all_workers_are_active(
        self, mock_reboot_worker, mock_multiplier_filter, mock_worker_filter
    ) -> None:
        # Mock workers
        worker = MagicMock(id=1, name="Seed 00")
        mock_worker_filter.return_value = [worker]

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

    @patch("orchestrator.tasks.Worker.objects.filter")
    @patch("orchestrator.tasks.Multiplier.objects.filter")
    @patch("orchestrator.tasks.reboot_worker")
    def test_some_workers_are_failing(
        self, mock_reboot_worker, mock_multiplier_filter, mock_worker_filter
    ) -> None:
        # Mock workers
        worker = MagicMock(id=1, name="Seed 00")
        mock_worker_filter.return_value = [worker]

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

    @patch("orchestrator.tasks.Multiplier.objects.filter")
    @patch("orchestrator.tasks.reboot_worker")
    @patch("orchestrator.tasks.BettingApp.list", return_value=["BETIKA", "BETGR8"])
    def test_only_workers_in_betting_apps_are_tested(
        self, mock_app_list, mock_reboot_worker, mock_multiplier_filter
    ):
        # Create mock workers
        Worker.objects.all().delete()  # Clear existing workers
        worker_in = Worker.objects.create(name="Seed 00", app="BETIKA")
        Worker.objects.create(name="Seed 01", app="NOT_BETTING_APP")

        # Only worker_in should be checked, simulate both are stale
        mock_queryset = MagicMock()
        mock_queryset.order_by.return_value = mock_queryset
        mock_queryset.values_list.return_value = mock_queryset
        mock_queryset.first.return_value = None
        mock_multiplier_filter.return_value = mock_queryset

        find_failing_workers()

        # Only worker_in should be rebooted
        mock_reboot_worker.assert_called_once_with(worker_in.id)


#
# import json
# from unittest import TestCase
# from unittest.mock import patch, MagicMock
#
# from orchestrator.tasks import find_failing_workers
#
#
# @patch("orchestrator.tasks.requests.get")
# @patch("orchestrator.tasks.Worker.objects.get")
# @patch("orchestrator.tasks.reboot_worker")
# @patch("orchestrator.tasks.BettingApp.list", return_value=["betgr8"])
# class TestFindFailingWorkers(TestCase):
#     def setUp(self):
#         self.mock_response = MagicMock()
#         self.mock_response.status_code = 200
#         self.mock_response.json.return_value = {
#             "kind": "PodMetricsList",
#             "apiVersion": "metrics.k8s.io/v1beta1",
#             "metadata": {},
#             "items": [
#                 {
#                     "metadata": {
#                         "name": "betgr8-seed-0",
#                         "namespace": "betgr8",
#                     },
#                     "containers": [
#                         {
#                             "name": "chrome-browser",
#                             "usage": {
#                                 "cpu": "998546457n",  # CPU usage above 0.5 cores
#                             }
#                         }
#                     ]
#                 },
#                 {
#                     "metadata": {
#                         "name": "betgr8-seed-1",
#                         "namespace": "betgr8",
#                     },
#                     "containers": [
#                         {
#                             "name": "chrome-browser",
#                             "usage": {
#                                 "cpu": "998337018n",  # CPU usage above 0.5 cores
#                             }
#                         }
#                     ]
#                 }
#             ]
#         }
#
#     def test_all_workers_cpu_above_threshold(self, mock_app_list, mock_reboot_worker, mock_worker_get, mock_request):
#         mock_request.return_value = self.mock_response
#
#         find_failing_workers()
#
#         mock_request.assert_called_once()
#         mock_worker_get.assert_not_called()
#         mock_reboot_worker.assert_not_called()
#
#     def test_some_pods_cpu_below_threshold(self, mock_app_list, mock_reboot_worker, mock_worker_get, mock_request):
#         self.mock_response.json.return_value["items"][0]["containers"][0]["usage"]["cpu"] = "400000000n"  # CPU usage below 0.5 cores
#         mock_request.return_value = self.mock_response
#
#         mock_worker = MagicMock()
#         mock_worker.id = 1
#         mock_worker_get.return_value = mock_worker
#
#         find_failing_workers()
#
#         mock_request.assert_called_once()
#         mock_worker_get.assert_called_once_with(name="Seed 00", app="BETGR8")
#         mock_reboot_worker.assert_called_once_with(mock_worker.id)
#
#     def test_only_pods_in_bettingapp_list_are_rebooted(self, mock_app_list, mock_reboot_worker, mock_worker_get, mock_request):
#         self.mock_response.json.return_value["items"].append(
#             {
#                 "metadata": {
#                     "name": "otherapp-seed-0",
#                     "namespace": "otherapp",
#                 },
#                 "containers": [
#                     {
#                         "name": "chrome-browser",
#                         "usage": {
#                             "cpu": "400000000n",  # CPU usage below 0.5 cores
#                         }
#                     }
#                 ]
#             }
#         )
#
#         mock_request.return_value.status_code = 200
#         mock_request.return_value = self.mock_response
#
#         mock_worker = MagicMock()
#         mock_worker.id = 1
#         mock_worker_get.return_value = mock_worker
#
#         find_failing_workers()
#
#         mock_reboot_worker.assert_not_called()
#         mock_worker_get.assert_not_called()
#         mock_request.assert_called_once()
