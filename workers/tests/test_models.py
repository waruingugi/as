from django.db.utils import IntegrityError
from django.test import TestCase

from commons.constants import BettingApps, SeedNames
from workers.models import Worker


class WorkerModelTests(TestCase):
    def setUp(self) -> None:
        self.app_name = BettingApps.BETIKA.value
        self.worker = Worker.objects.create(app=self.app_name, name=SeedNames.list()[0])

    def test_create_worker(self) -> None:
        self.assertEqual(self.worker.app, self.app_name)
        self.assertEqual(self.worker.name, SeedNames.list()[0])
        self.assertIsNotNone(self.worker.key)

    def test_worker_key_is_unique(self) -> None:
        worker1 = Worker.objects.create(app=self.app_name, name=SeedNames.list()[1])
        worker2 = Worker.objects.create(app=self.app_name, name=SeedNames.list()[2])

        self.assertNotEqual(self.worker.key, worker1.key)
        self.assertNotEqual(self.worker.key, worker2.key)
        self.assertNotEqual(worker1.key, worker2.key)

    def test_unique_worker_name_constraint_is_enforced(self) -> None:
        # Create the first Worker instance
        Worker.objects.create(app=BettingApps.BETIKA.value, name=SeedNames.list()[2])

        # Attempt to create a second Worker instance with the same name
        with self.assertRaises(IntegrityError) as context:
            Worker.objects.create(
                app=BettingApps.BETIKA.value, name=SeedNames.list()[2]
            )

        # Ensure the IntegrityError message indicates a unique constraint violation
        self.assertIn(
            "duplicate key value violates unique constraint", str(context.exception)
        )
