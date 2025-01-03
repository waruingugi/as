from django.urls import reverse
from rest_framework import status

from commons.constants import BettingApps
from commons.tests.test_base import UserBaseAPITestCase
from workers.models import Worker
from workers.serializers import WorkerListSerializer


class WorkerCreateAPIViewTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.create_url = reverse("workers:create")
        self.data = {"app": BettingApps.BETIKA.value, "name": "betika-node-001"}

    def test_create_worker_successfully_as_staff(self) -> None:
        self.force_authenticate_staff_user()
        response = self.client.post(self.create_url, self.data)
        self.assertIn("app", response.data)
        self.assertEqual(response.data["app"], BettingApps.BETIKA.value)

    def test_create_worker_as_user_is_forbidden(self) -> None:
        self.force_authenticate_user()
        response = self.client.post(self.create_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WorkerListViewTestCase(UserBaseAPITestCase):
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

    def test_list_workers_as_user_is_forbidden(self) -> None:
        self.force_authenticate_user()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
