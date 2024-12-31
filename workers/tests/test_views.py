from django.urls import reverse
from rest_framework.test import APITestCase

from commons.constants import BettingApps


class WorkerCreateAPIViewTests(APITestCase):
    def setUp(self) -> None:
        self.create_url = reverse("workers:create")
        self.data = {"app": BettingApps.BETIKA.value, "name": "betika-node-001"}

    # def test_create_worker_successfully(self) -> None:
    #     response = self.client.post(self.create_url, self.data)
    #     self.assertIn("app", response.data["app"])
    #     self.assertEqual(response.data["app"], BettingApps.BETIKA.value)
