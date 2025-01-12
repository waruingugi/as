from django.urls import reverse
from rest_framework import status

from commons.constants import BettingApps
from commons.tests.test_base import UserBaseAPITestCase
from workers.models import Worker
from workers.serializers import WorkerListSerializer


class WorkerCreateViewTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.create_url = reverse("workers:create")
        self.data = {"app": BettingApps.BETIKA.value, "name": "betika-node-001"}
        self.force_authenticate_staff_user()

    def test_create_worker_successfully_as_staff(self) -> None:
        response = self.client.post(self.create_url, self.data)
        self.assertIn("app", response.data)
        self.assertEqual(response.data["app"], BettingApps.BETIKA.value)

    def test_invalid_worker_name(self) -> None:
        data = {"app": "invalid_worker_name", "name": "betika-node-001"}
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_worker_as_user_is_forbidden(self) -> None:
        self.force_authenticate_user()
        response = self.client.post(self.create_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WorkerListViewTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.list_url = reverse("workers:list")
        Worker.objects.bulk_create(
            [
                Worker(name="betika-node-001", app=BettingApps.BETIKA.value),
                Worker(name="betika-node-002", app=BettingApps.BETIKA.value),
                Worker(name="betika-node-003", app=BettingApps.BETIKA.value),
            ]
        )
        self.force_authenticate_staff_user()

    def test_list_workers_as_staff(self) -> None:
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        workers = Worker.objects.all()
        serializer = WorkerListSerializer(workers, many=True)
        self.assertEqual(response.data["results"], serializer.data)

    def test_response_is_paginated(self) -> None:
        response = self.client.get(self.list_url, {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_search_workers_as_staff(self) -> None:
        response = self.client.get(self.list_url, {"search": "betika-node-001"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "betika-node-001")

    def test_ordering_workers_as_staff(self) -> None:
        response = self.client.get(self.list_url, {"ordering": "created_at"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertTrue(
            results[0]["created_at"]
            <= results[1]["created_at"]
            <= results[2]["created_at"]
        )

    def test_filter_workers_by_app(self) -> None:
        response = self.client.get(self.list_url, {"app": BettingApps.BETIKA.value})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure that all returned workers have the app field set to 'BETIKA'
        for worker in response.data["results"]:
            self.assertEqual(worker["app"], BettingApps.BETIKA.value)

        # Verify the correct number of workers are returned
        self.assertEqual(len(response.data["results"]), 3)

    def test_permission_denied_for_non_staff(self) -> None:
        self.force_authenticate_user()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WorkerRetrieveUpdateViewTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        # Create a test worker
        self.worker = Worker.objects.create(
            name="betika-node-001", app=BettingApps.BETIKA.value
        )

        # Set the endpoint URL
        self.url = reverse("workers:detail", kwargs={"id": self.worker.id})
        self.force_authenticate_staff_user()

    def test_can_retrieve_worker_as_staff(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], self.worker.name)
        self.assertEqual(response.data["app"], self.worker.app)

    def test_can_update_worker_as_staff(self):
        update_data = {"name": "betika-node-004"}
        response = self.client.patch(self.url, update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.name, "betika-node-004")
        self.assertEqual(self.worker.app, BettingApps.BETIKA.value)

    def test_cannot_update_worker_as_regular_user(self):
        self.force_authenticate_user()
        update_data = {"name": "betika-node-004"}
        response = self.client.patch(self.url, update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_retrieve_worker_as_regular_user(self):
        self.force_authenticate_user()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
