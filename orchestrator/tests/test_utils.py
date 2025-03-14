from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import override_settings

from commons.constants import CacheKeys
from orchestrator.utils import (
    calculate_jaccard_similarity,
    find_similar_workers,
    reboot_worker,
)


class TestJaccardSimilarity(TestCase):
    def test_identical_sets(self) -> None:
        set_1 = {1, 2, 3}
        set_2 = {1, 2, 3}
        similarity = calculate_jaccard_similarity(set_1, set_2)
        self.assertEqual(
            similarity, 1.0, "Identical sets should have similarity of 1.0"
        )

    def test_completely_different_sets(self) -> None:
        set_1 = {1, 2, 3}
        set_2 = {4, 5, 6}
        similarity = calculate_jaccard_similarity(set_1, set_2)
        self.assertEqual(
            similarity, 0.0, "Completely different sets should have similarity of 0.0"
        )

    def test_partially_overlapping_sets(self) -> None:
        set_1 = {1, 2, 3}
        set_2 = {2, 3, 4}
        similarity = calculate_jaccard_similarity(set_1, set_2)
        expected_similarity = 2 / 4  # Intersection: {2, 3}, Union: {1, 2, 3, 4}
        self.assertAlmostEqual(similarity, expected_similarity, places=2)

    def test_empty_sets(self) -> None:
        set_1 = set()
        set_2 = set()
        similarity = calculate_jaccard_similarity(set_1, set_2)
        self.assertEqual(similarity, 0.0, "Empty sets should have similarity of 0.0")

    def test_one_empty_one_non_empty_set(self) -> None:
        set_1 = {1, 2, 3}
        set_2 = set()
        similarity = calculate_jaccard_similarity(set_1, set_2)
        self.assertEqual(similarity, 0.0, "One empty set should have similarity of 0.0")


class TestFindSimilarWorkers(TestCase):
    def test_no_workers(self):
        worker_payouts = {}
        matched_workers = find_similar_workers(worker_payouts)
        self.assertEqual(
            matched_workers, {}, "No workers should return an empty result."
        )

    def test_no_similarity(self) -> None:
        worker_payouts = {
            1: {1, 2, 3},
            2: {4, 5, 6},
            3: {7, 8, 9},
        }
        matched_workers = find_similar_workers(worker_payouts)
        self.assertEqual(
            matched_workers, {}, "Workers with no overlap should not be matched."
        )

    def test_exact_similarity(self) -> None:
        worker_payouts = {
            1: {1, 2, 3},
            2: {1, 2, 3},
            3: {4, 5, 6},
        }
        matched_workers = find_similar_workers(worker_payouts)
        self.assertEqual(
            matched_workers,
            {(1, 2): 1.0},
            "Workers with identical sets should be matched with similarity 1.0.",
        )

    def test_partial_similarity(self) -> None:
        worker_payouts = {
            1: {1, 2, 3},
            2: {2, 3, 4},
            3: {5, 6, 7},
        }
        matched_workers = find_similar_workers(worker_payouts, threshold=0.5)
        self.assertEqual(
            matched_workers,
            {(1, 2): 0.5},
            "Workers with partial overlap should be matched if above the threshold.",
        )

    def test_custom_threshold(self) -> None:
        worker_payouts = {
            1: {1, 2, 3},
            2: {2, 3, 4},
            3: {5, 6, 7},
        }
        matched_workers = find_similar_workers(worker_payouts, threshold=0.6)
        self.assertEqual(
            matched_workers,
            {},
            "With a threshold of 0.6, partially overlapping workers should not be matched.",
        )


class TestRebootWorker(TestCase):
    def tearDown(self):
        # Clear the cache after each test
        cache.clear()

    @patch("orchestrator.utils.Worker.objects.get")
    @patch("orchestrator.utils.requests.delete")
    @override_settings(KUBERNETES_API_BASE_URL="https://63.150.79.21:443")
    @override_settings(KUBERNETES_TOKEN="mock_token")
    def test_successful_pod_reboot(self, mock_delete, mock_get) -> None:
        # Mock worker object
        worker_mock = MagicMock()
        worker_mock.name = "Seed 00"
        worker_mock.app = "Betika"
        mock_get.return_value = worker_mock

        # Mock successful DELETE request
        mock_delete.return_value.status_code = 200

        # Call the function
        reboot_worker(worker_id=1)

        # Assertions
        mock_get.assert_called_once_with(id=1)
        mock_delete.assert_called_once_with(
            "https://63.150.79.21:443/api/v1/namespaces/betika/pods/betika-seed-0",
            headers={"Authorization": "Bearer mock_token"},
            verify=False,
        )

        # Assert cache key is set
        cache_key = CacheKeys.REBOOTED_WORKER.format(str(1))
        self.assertIsNotNone(cache.get(cache_key))
        self.assertTrue(cache.get(cache_key))

    @patch("orchestrator.utils.Worker.objects.get")
    @patch("orchestrator.utils.requests.delete")
    @override_settings(KUBERNETES_API_BASE_URL="https://63.150.79.21:443")
    @override_settings(KUBERNETES_TOKEN="mock_token")
    def test_failed_api_request(self, mock_delete, mock_get) -> None:
        # Mock worker object
        worker_mock = MagicMock()
        worker_mock.name = "Seed 01"
        worker_mock.app = "Betika"
        mock_get.return_value = worker_mock

        # Mock failed DELETE request
        mock_delete.return_value.status_code = 500
        mock_delete.return_value.text = "Internal Server Error"

        # Call the function
        reboot_worker(worker_id=2)

        # Assertions
        mock_delete.assert_called_once_with(
            "https://63.150.79.21:443/api/v1/namespaces/betika/pods/betika-seed-1",
            headers={"Authorization": "Bearer mock_token"},
            verify=False,
        )

    @patch("orchestrator.utils.Worker.objects.get")
    def test_worker_already_rebooted(self, mock_get) -> None:
        # Mock worker object
        worker_mock = MagicMock()
        worker_mock.name = "Seed 02"
        worker_mock.app = "Betika"
        mock_get.return_value = worker_mock

        # Add worker to cache as already rebooted
        cache.set("rebooted_worker:3", "1", timeout=600)

        # Call the function
        reboot_worker(worker_id=3)

        # Assertions
        mock_get.assert_called_once_with(id=3)

    @patch("orchestrator.utils.Worker.objects.get")
    @patch("orchestrator.utils.os.getenv")
    @patch("orchestrator.utils.requests.delete")
    def test_missing_environment_variables(
        self, mock_delete_request, mock_getenv, mock_get
    ) -> None:
        # Mock environment variables as missing
        mock_getenv.side_effect = lambda key: None

        # Mock response as failed
        mock_delete_request.return_value.status_code = 500

        # Mock worker object
        worker_mock = MagicMock()
        worker_mock.name = "Seed 03"
        worker_mock.app = "Betika"
        mock_get.return_value = worker_mock

        # Call the function
        reboot_worker(worker_id=4)

        # Assertions
        self.assertIsNone(mock_getenv("KUBERNETES_API_BASE_URL"))
        self.assertIsNone(mock_getenv("KUBERNETES_TOKEN"))
