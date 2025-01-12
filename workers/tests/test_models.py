from django.test import TestCase

from commons.constants import BettingApps
from workers.models import Worker


class WorkerModelTests(TestCase):
    def setUp(self) -> None:
        self.app_name = "betika-node-01"
        self.worker = Worker.objects.create(
            app=self.app_name, name=BettingApps.BETIKA.value
        )

    def test_create_worker(self) -> None:
        self.assertEqual(self.worker.app, self.app_name)
        self.assertEqual(self.worker.name, BettingApps.BETIKA.value)
        self.assertIsNotNone(self.worker.key)

    def test_worker_key_is_unique(self) -> None:
        worker1 = Worker.objects.create(app="betika-node-02", name="worker-1")
        worker2 = Worker.objects.create(app="betika-node-03", name="worker-2")

        self.assertNotEqual(self.worker.key, worker1.key)
        self.assertNotEqual(self.worker.key, worker2.key)
        self.assertNotEqual(worker1.key, worker2.key)
