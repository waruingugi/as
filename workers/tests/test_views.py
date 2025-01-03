from django.urls import reverse

from commons.constants import BettingApps
from commons.tests.test_base import UserBaseAPITestCase


class WorkerCreateAPIViewTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.create_url = reverse("workers:create")
        self.data = {"app": BettingApps.BETIKA.value, "name": "betika-node-001"}
        self.force_authenticate_staff_user()

    def test_create_worker_successfully(self) -> None:
        response = self.client.post(self.create_url, self.data)
        self.assertIn("app", response.data)
        self.assertEqual(response.data["app"], BettingApps.BETIKA.value)
