from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from commons.constants import BettingApp, CacheKeys, SeedName
from commons.tests.test_base import UserBaseAPITestCase
from observers.models import Multiplier
from workers.models import Worker
from workers.serializers import WorkerListSerializer


class WorkerCreateViewTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.create_url = reverse("workers:create")
        self.data = {"app": BettingApp.BETIKA.value, "name": SeedName.list()[0]}
        self.force_authenticate_staff_user()

    def test_create_worker_successfully_as_staff(self) -> None:
        response = self.client.post(self.create_url, self.data)
        self.assertIn("app", response.data)
        self.assertEqual(response.data["app"], BettingApp.BETIKA.value)

    def test_unique_worker_key_constraint_is_enforced(self) -> None:
        response1 = self.client.post(
            self.create_url,
            {"app": BettingApp.BETIKA.value, "name": SeedName.list()[0]},
        )
        response2 = self.client.post(
            self.create_url,
            {"app": BettingApp.BETIKA.value, "name": SeedName.list()[1]},
        )
        self.assertNotEqual(response1.data["key"], response2.data["key"])

    def test_unique_worker_name_constraint_is_enforced(self) -> None:
        self.client.post(
            self.create_url,
            {"app": BettingApp.BETIKA.value, "name": SeedName.list()[2]},
        )
        response = self.client.post(
            self.create_url,
            {"app": BettingApp.BETIKA.value, "name": SeedName.list()[2]},
        )
        self.assertEqual(
            response.data["non_field_errors"],
            ["The fields app, name must make a unique set."],
        )

    def test_invalid_worker_name(self) -> None:
        data = {"app": "invalid_worker_name", "name": SeedName.list()[1]}
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
                Worker(name=SeedName.list()[0], app=BettingApp.BETIKA.value),
                Worker(name=SeedName.list()[1], app=BettingApp.BETIKA.value),
                Worker(name=SeedName.list()[2], app=BettingApp.BETIKA.value),
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
        response = self.client.get(self.list_url, {"search": SeedName.list()[1]})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], SeedName.list()[1])

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
        response = self.client.get(self.list_url, {"app": BettingApp.BETIKA.value})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure that all returned workers have the app field set to 'BETIKA'
        for worker in response.data["results"]:
            self.assertEqual(worker["app"], BettingApp.BETIKA.value)

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
            name=SeedName.list()[1], app=BettingApp.BETIKA.value
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
        update_data = {"name": SeedName.list()[0]}
        response = self.client.patch(self.url, update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.worker.refresh_from_db()
        self.assertEqual(self.worker.name, SeedName.list()[0])
        self.assertEqual(self.worker.app, BettingApp.BETIKA.value)

    def test_cannot_update_worker_as_regular_user(self):
        self.force_authenticate_user()
        update_data = {"name": SeedName.list()[0]}
        response = self.client.patch(self.url, update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_retrieve_worker_as_regular_user(self):
        self.force_authenticate_user()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WorkersHealthViewTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.health_url = reverse(
            "workers:health", kwargs={"app": BettingApp.BETIKA.value}
        )

        self.worker = Worker.objects.create(
            name=SeedName.list()[0], app=BettingApp.BETIKA.value
        )
        self.force_authenticate_staff_user()

    def tearDown(self) -> None:
        cache.clear()

    def test_worker_health_status_ok(self) -> None:
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["status"], "ok")

    def test_worker_health_status_error(self) -> None:
        cache.set(
            CacheKeys.WORKER_IS_HEALTHY.format(self.worker.id), False, timeout=60 * 10
        )
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["status"], "error")

    def test_no_workers_found(self) -> None:
        Worker.objects.all().delete()
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "No workers found")


class WorkerDeleteViewTests(UserBaseAPITestCase):
    def setUp(self):
        self.worker = Worker.objects.create(
            app=BettingApp.BETIKA.value, name=SeedName.list()[0]
        )
        self.multiplier1 = Multiplier.objects.create(crash=1.25, worker=self.worker)
        self.multiplier2 = Multiplier.objects.create(crash=3.75, worker=self.worker)
        self.delete_url = reverse("workers:delete", args=[self.worker.id])

        self.force_authenticate_staff_user()

    def test_delete_worker(self):
        response = self.client.delete(self.delete_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Worker.objects.filter(id=self.worker.id).exists())

    def test_cascade_delete_multipliers(self):
        self.client.delete(self.delete_url)
        self.assertFalse(Multiplier.objects.filter(worker=self.worker).exists())
