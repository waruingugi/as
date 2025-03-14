from django.db.utils import IntegrityError
from django.test import TestCase

from commons.constants import BettingApp, SeedName
from workers.models import Worker


class WorkerModelTests(TestCase):
    def setUp(self) -> None:
        self.app_name = BettingApp.BETIKA.value
        self.worker = Worker.objects.create(app=self.app_name, name=SeedName.list()[0])

    def test_create_worker(self) -> None:
        self.assertEqual(self.worker.app, self.app_name)
        self.assertEqual(self.worker.name, SeedName.list()[0])
        self.assertIsNotNone(self.worker.key)

    def test_worker_key_is_unique(self) -> None:
        worker1 = Worker.objects.create(app=self.app_name, name=SeedName.list()[1])
        worker2 = Worker.objects.create(app=self.app_name, name=SeedName.list()[2])

        self.assertNotEqual(self.worker.key, worker1.key)
        self.assertNotEqual(self.worker.key, worker2.key)
        self.assertNotEqual(worker1.key, worker2.key)

    def test_unique_worker_name_constraint_is_enforced(self) -> None:
        # Create the first Worker instance
        Worker.objects.create(app=BettingApp.BETIKA.value, name=SeedName.list()[2])

        # Attempt to create a second Worker instance with the same name
        with self.assertRaises(IntegrityError) as context:
            Worker.objects.create(app=BettingApp.BETIKA.value, name=SeedName.list()[2])

        # Ensure the IntegrityError message indicates a unique constraint violation
        self.assertIn(
            "duplicate key value violates unique constraint", str(context.exception)
        )

    def test_worker_with_different_name_same_seed_is_created_successfully(self) -> None:
        # Create the first Worker instance with a specific seed name
        Worker.objects.create(app=BettingApp.BETGR8.value, name=SeedName.SEED_O2.value)

        # Create a second Worker instance with a different name but same seed name
        worker = Worker.objects.create(
            app=BettingApp.BETIKA.value, name=SeedName.SEED_O2.value
        )

        # Ensure the second Worker instance is created successfully
        self.assertIsNotNone(worker)
