from unittest.mock import patch
from uuid import uuid4

from django.core.cache import cache
from django.test import TestCase

from commons.constants import DEFAULT_CACHE_DURATION, BettingApp, CacheKeys, SeedName
from observers.models import Multiplier
from observers.utils import (
    get_new_multipliers,
    get_worker_crash_list,
    get_workers_crash_history,
)
from workers.models import Worker


class GetNewMultipliersTestCase(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.multipliers_list = [1.21, 4.33, 1.18]
        cls.worker = Worker.objects.create(
            app=BettingApp.BETIKA.value, name=SeedName.list()[0], key=uuid4()
        )

    @classmethod
    def tearDownClass(cls) -> None:
        Worker.objects.all().delete()

    def test_new_multipliers_when_model_is_empty(self) -> None:
        """Test the func. returns all multipliers when the Multiplier model is empty"""
        new_multipliers = get_new_multipliers(
            worker_id=self.worker.id,  # type: ignore
            new_multipliers_list=self.multipliers_list,  # type: ignore
        )
        self.assertListEqual(new_multipliers, self.multipliers_list)

    def test_new_multipliers_when_model_is_not_empty(self) -> None:
        """Test the func. returns only the new payouts"""
        objs = [
            Multiplier(worker=self.worker, crash=crash)
            for crash in self.multipliers_list[::-1]
        ]  # type: ignore
        Multiplier.objects.bulk_create(objs)

        new_multipliers_list = get_new_multipliers(
            worker_id=self.worker.id,  # type: ignore
            new_multipliers_list=[5.67, 1.00, 1.21] + self.multipliers_list,
        )

        self.assertListEqual(new_multipliers_list, [5.67, 1.00, 1.21])


class TestGetWorkerCrashList(TestCase):
    def setUp(self) -> None:
        self.worker = Worker.objects.create(
            app=BettingApp.BETIKA.value, name=SeedName.SEED_00.value
        )
        self.multipliers = [
            Multiplier.objects.create(worker=self.worker, crash=15.5),
            Multiplier.objects.create(worker=self.worker, crash=10.0),
            Multiplier.objects.create(worker=self.worker, crash=5.0),
        ]

    def test_get_worker_crash_list_returns_correct_data(self) -> None:
        result = get_worker_crash_list(self.worker.id, count=2)  # type: ignore
        self.assertEqual(len(result), 2)
        self.assertEqual(float(result[0]["crash"]), self.multipliers[2].crash)
        self.assertEqual(float(result[1]["crash"]), self.multipliers[1].crash)

    def test_get_worker_crash_list_empty_worker(self) -> None:
        empty_worker = Worker.objects.create(
            app=BettingApp.BETIKA.value, name=SeedName.SEED_01.value
        )
        result = get_worker_crash_list(empty_worker.id, count=2)  # type: ignore
        self.assertEqual(result, [])


class TestGetWorkersCrashHistory(TestCase):
    def setUp(self) -> None:
        self.worker1 = Worker.objects.create(
            app=BettingApp.BETIKA.value, name=SeedName.SEED_00.value
        )
        self.worker2 = Worker.objects.create(
            app=BettingApp.BETIKA.value, name=SeedName.SEED_01.value
        )

        self.multipliers_worker1 = [
            Multiplier.objects.create(worker=self.worker1, crash=15.5),
            Multiplier.objects.create(worker=self.worker1, crash=10.0),
        ]

        self.multipliers_worker2 = [
            Multiplier.objects.create(worker=self.worker2, crash=7.0),
            Multiplier.objects.create(worker=self.worker2, crash=5.0),
        ]

    @patch("observers.utils.get_worker_crash_list")
    def test_get_workers_crash_history_recompute(
        self, mock_get_worker_crash_list
    ) -> None:
        mock_get_worker_crash_list.side_effect = lambda worker_id, count: [
            {"created_at": "2025-01-26T10:00:00Z", "crash": 20.0}
        ]

        result = get_workers_crash_history(
            app=BettingApp.BETIKA.value, count=1, recompute=True
        )
        self.assertEqual(len(result), 2)
        self.assertIn(self.worker1.id, [result[0]["id"], result[1]["id"]])
        self.assertIn(self.worker2.id, [result[0]["id"], result[1]["id"]])
        mock_get_worker_crash_list.assert_called()

    def test_get_workers_crash_history_cache(self) -> None:
        cache_key_worker1 = CacheKeys.WORKER_CRASH_QUERY.format(self.worker1.id)
        cache_key_worker2 = CacheKeys.WORKER_CRASH_QUERY.format(self.worker2.id)

        cache.set(
            cache_key_worker1,
            [{"created_at": "2025-01-26T10:00:00Z", "crash": 20.0}],
            DEFAULT_CACHE_DURATION,
        )
        cache.set(
            cache_key_worker2,
            [{"created_at": "2025-01-26T11:00:00Z", "crash": 15.0}],
            DEFAULT_CACHE_DURATION,
        )

        result = get_workers_crash_history(
            app=BettingApp.BETIKA.value, count=1, recompute=False
        )
        self.assertEqual(len(result), 2)

        crash_values = [entry["crash"] for entry in result]
        self.assertIn(
            [{"created_at": "2025-01-26T10:00:00Z", "crash": 20.0}], crash_values
        )
        self.assertIn(
            [{"created_at": "2025-01-26T11:00:00Z", "crash": 15.0}], crash_values
        )

    def test_get_workers_crash_history_empty_workers(self) -> None:
        result = get_workers_crash_history(app="NON_EXISTENT_APP", count=1)
        self.assertEqual(result, [])
