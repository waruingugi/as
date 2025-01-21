from uuid import uuid4

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from commons.constants import BettingApps, SeedNames
from commons.tests.test_base import UserBaseAPITestCase
from observers.models import Multiplier
from workers.models import Worker


class MultiplierCreateViewTests(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.create_url = reverse("multipliers:create")
        self.worker = Worker.objects.create(
            app=BettingApps.BETIKA.value, name=SeedNames.list()[0], key=uuid4().hex
        )
        self.data = {"multipliers": "1.32x, 1.41x, 2.09x, 3.12x"}

    def test_create_multipliers_successfully(self) -> None:
        response = self.client.post(
            self.create_url, self.data, HTTP_API_KEY=f"{self.worker.key}"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Multiplier.objects.count(), 4)
        self.assertEqual(float(Multiplier.objects.first().crash), 1.32)  # type: ignore

    def test_missing_api_key_raises_error(self) -> None:
        response = self.client.post(self.create_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MultiplierListViewTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.worker = Worker.objects.create(
            app=BettingApps.BETIKA.value, name=SeedNames.list()[0], key=uuid4().hex
        )
        self.multiplier_1 = Multiplier.objects.create(worker=self.worker, crash=1.51)
        self.multiplier_2 = Multiplier.objects.create(worker=self.worker, crash=2.55)
        self.url = reverse("multipliers:list")
        self.force_authenticate_staff_user()

    def test_permission_granted_for_staff(self):
        """Ensure staff users can access the endpoint."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_pagination(self):
        """Test pagination in the API response."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(
            len(response.data["results"]), 2
        )  # Adjust if more data is added

    def test_search_filter(self):
        """Test search functionality on the 'name' field."""
        response = self.client.get(f"{self.url}?search={self.worker.name}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)  # Matches all worker names

    def test_filtering(self):
        """Test filtering on the 'app' field."""
        response = self.client.get(f"{self.url}?app={BettingApps.BETIKA.value}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)  # No matches

    def test_ordering(self):
        """Test ordering functionality."""
        response = self.client.get(f"{self.url}?ordering=-created_at")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            float(response.data["results"][0]["crash"]), float(self.multiplier_2.crash)
        )

    def test_permission_denied_for_non_staff(self):
        """Ensure non-staff users cannot access the endpoint."""
        self.force_authenticate_user()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
