import json
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from commons.constants import BettingApp, SeedName
from commons.tests.test_base import UserBaseAPITestCase
from workers.models import Worker


class TestWorkerProbabilitiesView(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.valid_app_name = BettingApp.BETIKA.value
        self.invalid_app_name = "INVALID_APP"

        # Create mock workers
        self.worker1 = Worker.objects.create(
            app=self.valid_app_name, name=SeedName.SEED_00.value
        )
        self.worker2 = Worker.objects.create(
            app=self.valid_app_name, name=SeedName.SEED_01.value
        )

        self.url = reverse("probabilities:detail", args=[self.valid_app_name])
        self.force_authenticate_user()

    @patch("analytics.utils.format_worker_probabilities")
    def test_get_probabilities_valid_app(
        self, mock_format_worker_probabilities
    ) -> None:
        # Mock the response of format_worker_probabilities
        mock_format_worker_probabilities.side_effect = [
            {
                "id": self.worker1.id,
                "name": self.worker1.name,
                "probability": {"over_20x": {"probability": 0.15, "suggestion": ""}},
            },
            {
                "id": self.worker2.id,
                "name": self.worker2.name,
                "probability": {"over_20x": {"probability": 0.20, "suggestion": ""}},
            },
        ]

        response = self.client.get(self.url)
        worker_ids = [response.data[0]["id"], response.data[1]["id"]]

        # Assert the response is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the response data matches the mock data
        self.assertEqual(len(response.data), 2)

        self.assertIn(str(self.worker1.id), worker_ids)
        self.assertIn(str(self.worker2.id), worker_ids)

    def test_get_probabilities_invalid_app(self) -> None:
        invalid_url = reverse("probabilities:detail", args=[self.invalid_app_name])
        response = self.client.get(invalid_url)

        # Assert the response is 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_probabilities_no_workers(self) -> None:
        Worker.objects.all().delete()  # Remove all workers
        response = self.client.get(self.url)

        # Assert the response is 404 Not Found
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestWorkerProbabilitiesStreamView(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.valid_app_name = BettingApp.BETIKA.value
        self.invalid_app_name = "INVALID_APP"

        self.worker1 = Worker.objects.create(
            app=self.valid_app_name, name=SeedName.SEED_00.value
        )
        self.worker2 = Worker.objects.create(
            app=self.valid_app_name, name=SeedName.SEED_01.value
        )

        self.url = reverse("probabilities:stream", args=[self.valid_app_name])
        self.force_authenticate_user()

    @patch("analytics.utils.format_worker_probabilities")
    def test_stream_probabilities_valid_app(
        self, mock_format_worker_probabilities
    ) -> None:
        mock_format_worker_probabilities.side_effect = [
            {
                "id": self.worker1.id,
                "name": self.worker1.name,
                "probability": {"over_20x": {"probability": 0.15, "suggestion": ""}},
            },
            {
                "id": self.worker2.id,
                "name": self.worker2.name,
                "probability": {"over_20x": {"probability": 0.20, "suggestion": ""}},
            },
        ]

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # StreamingHttpResponse returns a bytes iterator, so decode and load JSON
        content = b"".join(response.streaming_content).decode()
        data = json.loads(content)

        self.assertEqual(len(data), 2)
        worker_ids = [str(self.worker1.id), str(self.worker2.id)]
        self.assertIn(str(data[0]["id"]), worker_ids)
        self.assertIn(str(data[1]["id"]), worker_ids)

    def test_stream_probabilities_invalid_app(self) -> None:
        invalid_url = reverse("probabilities:stream", args=[self.invalid_app_name])
        response = self.client.get(invalid_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_stream_probabilities_no_workers(self) -> None:
        Worker.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
