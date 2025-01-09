from uuid import uuid4

from django.test import TestCase

from commons.constants import BettingApps
from observers.models import Multiplier
from workers.models import Worker


class MultiplierModelTests(TestCase):
    def setUp(self) -> None:
        # Create a Worker instance
        self.worker = Worker.objects.create(
            app=BettingApps.BETIKA.value, name="betika-node-001", key=uuid4().hex
        )

        # Create Multiplier instances
        self.multiplier1 = Multiplier.objects.create(crash=1.25, worker=self.worker)
        self.multiplier2 = Multiplier.objects.create(crash=3.75, worker=self.worker)

    def test_multiplier_creation(self) -> None:
        # Test if multipliers are created correctly
        self.assertEqual(self.multiplier1.crash, 1.25)
        self.assertEqual(self.multiplier1.worker, self.worker)
        self.assertEqual(self.multiplier2.crash, 3.75)
        self.assertEqual(self.multiplier2.worker, self.worker)

    def test_worker_related_name(self) -> None:
        # Test the related_name attribute for worker
        related_multipliers = self.worker.multipliers.all()
        self.assertIn(self.multiplier1, related_multipliers)
        self.assertIn(self.multiplier2, related_multipliers)
        self.assertEqual(related_multipliers.count(), 2)

    def test_string_representation(self) -> None:
        # Test the string representation if __str__ is defined
        self.assertEqual(str(self.multiplier1), str(self.multiplier1.crash))
        self.assertEqual(str(self.multiplier2), str(self.multiplier2.crash))

    def test_cascade_delete(self):
        # Test that deleting a Worker also deletes associated Multipliers
        worker_id = self.worker.id  # Save the worker ID before deletion
        self.worker.delete()
        self.assertFalse(Multiplier.objects.filter(worker_id=worker_id).exists())
