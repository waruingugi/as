import unittest
from unittest.mock import patch
from uuid import uuid4

from django.core.cache import cache
from django.test import TestCase

from commons.constants import DEFAULT_CACHE_DURATION, BettingApp, CacheKeys, SeedName
from observers.models import Multiplier
from observers.utils import (  # SignalNotificationMonitor,
    get_new_multipliers,
    get_worker_crash_list,
    get_workers_crash_history,
    set_room_name,
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


# class TestSignalNotificationMonitor(TestCase):
#     def setUp(self) -> None:
#         self.monitor = SignalNotificationMonitor
#         self.mock_instance = type(
#             "MockInstance",
#             (),
#             {
#                 "id": uuid4(),
#                 "crash": 100,
#                 "worker": type(
#                     "MockWorker",
#                     (),
#                     {
#                         "app": BettingApp.BETIKA.value,
#                         "name": "Seed 00",
#                         "id": uuid4(),
#                     },
#                 )(),
#                 "created_at": self._mock_created_at(),
#             },
#         )()
#
#     def tearDown(self):
#         cache.clear()
#
#     def _mock_created_at(self):
#         # Provide a datetime object for created_at
#         import datetime
#
#         return datetime.datetime(2025, 1, 26, 12, 0, 0)
#
#     @patch("observers.utils.Probability.calculate_probability", return_value=100)
#     @patch("observers.utils.send_push_task")
#     @patch(
#         "observers.utils.get_app_threshold_subscribers", return_value={"user1", "user2"}
#     )
#     def test_process_latest_payout_triggers_notification(
#         self, mock_get_subs, mock_send_push, mock_calc_prob
#     ) -> None:
#         """Assert the notification is triggered correctly for all seeds and thresholds"""
#         for seed in SeedName.list():
#             self.mock_instance.worker.name = seed
#             self.monitor.process_latest_payout(self.mock_instance)
#             # Check that notification was sent for each threshold crossed
#             calls = [
#                 call.kwargs["user_ids"] for call in mock_send_push.delay.call_args_list
#             ]
#
#             self.assertTrue(any({"user1", "user2"} == set(ids) for ids in calls))
#             mock_send_push.delay.reset_mock()
#
#     @patch("observers.utils.send_push_task")
#     @patch("observers.utils.get_app_threshold_subscribers", return_value=set())
#     def test_process_latest_payout_when_no_subscribers(
#         self, mock_get_subs, mock_send_push
#     ) -> None:
#         """Assert no notification is sent when there are no subscribers for any seed"""
#         for seed in SeedName.list():
#             self.mock_instance.worker.name = seed
#             self.monitor.process_latest_payout(self.mock_instance)
#             mock_send_push.delay.assert_not_called()
#
#     @patch("observers.utils.send_push_task")
#     def test_process_latest_payout_resets_flags_when_payout_below_reset(
#         self, mock_send_push
#     ) -> None:
#         """Assert the flags are reset when the payout is below the reset threshold for all seeds"""
#         self.mock_instance.crash = 10  # Set payout below the reset threshold
#
#         # Set a flag in cache to simulate a previous trigger
#         for threshold in self.monitor.THRESHOLDS:
#             key = self.monitor._flag_key(
#                 self.mock_instance.worker.app,
#                 self.mock_instance.worker.name,
#                 threshold,
#             )
#             cache.set(key, "dummy", timeout=None)
#
#         self.monitor.process_latest_payout(self.mock_instance)
#
#         # Assert all flags are cleared from cache
#         for threshold in self.monitor.THRESHOLDS:
#             key = self.monitor._flag_key(
#                 self.mock_instance.worker.app,
#                 self.mock_instance.worker.name,
#                 threshold,
#             )
#             self.assertIsNone(cache.get(key))
#         mock_send_push.delay.assert_not_called()
#
#     @patch("observers.utils.send_push_task")
#     def test_batch_reset_all_resets_all_flags(self, mock_send_push) -> None:
#         """Assert batch_reset_all clears all flags for all apps, seeds, and thresholds"""
#         # Set all flags in cache
#         for app in BettingApp.list():
#             for seed in SeedName.list():
#                 for threshold in self.monitor.THRESHOLDS:
#                     key = self.monitor._flag_key(app, seed, threshold)
#                     cache.set(key, "dummy", timeout=None)
#         self.monitor.batch_reset_all()
#         # Assert all flags are cleared
#         for app in BettingApp.list():
#             for seed in SeedName.list():
#                 for threshold in self.monitor.THRESHOLDS:
#                     key = self.monitor._flag_key(app, seed, threshold)
#                     self.assertIsNone(cache.get(key))
#
#     def test_send_notification(self):
#         """Test that _send_notification calls send_push_task with correct arguments."""
#         with (
#             patch("observers.utils.send_push_task") as mock_send_push,
#             patch(
#                 "observers.utils.get_app_threshold_subscribers",
#                 return_value={"user1", "user2"},
#             ),
#         ):
#             self.monitor._send_notification(
#                 app=self.mock_instance.worker.app,
#                 seed=self.mock_instance.worker.name,
#                 threshold=50,
#             )
#             mock_send_push.delay.assert_called_once()
#             args, kwargs = mock_send_push.delay.call_args
#             self.assertEqual(set(kwargs["user_ids"]), {"user1", "user2"})


class TestSetRoomName(unittest.TestCase):
    @patch("observers.utils.cache")
    @patch("observers.utils.CacheKeys")
    def test_set_room_name_with_room_no(self, mock_cache_keys, mock_cache):
        mock_cache_keys.SEED_TO_ROOM_MAPPING = "{}:{}"
        app = "TestApp"
        worker_name = "Seed 01"
        room_no = 2
        expected_room_name = "Room 02"
        expected_cache_key = "TestApp:Seed 01"

        set_room_name(app=app, worker_name=worker_name, room_no=room_no)

        mock_cache.set.assert_called_once_with(
            expected_cache_key, expected_room_name, unittest.mock.ANY
        )

    @patch("observers.utils.cache")
    @patch("observers.utils.CacheKeys")
    def test_set_room_name_without_room_no(self, mock_cache_keys, mock_cache):
        mock_cache_keys.SEED_TO_ROOM_MAPPING = "{}:{}"
        app = "TestApp"
        worker_name = "Seed 01"
        expected_room_name = "Room 01"
        expected_cache_key = "TestApp:Seed 01"

        set_room_name(app=app, worker_name=worker_name)

        mock_cache.set.assert_called_once_with(
            expected_cache_key, expected_room_name, unittest.mock.ANY
        )


# class TestSignalNotificationMonitor(TestCase):
#     def setUp(self) -> None:
#         self.monitor = SignalNotificationMonitor
#         self.mock_instance = type(
#             "MockInstance",
#             (),
#             {
#                 "crash": 100,
#                 "worker": type(
#                     "MockWorker",
#                     (),
#                     {"app": BettingApp.BETIKA.value, "name": "TestWorker"},
#                 )(),
#                 "created_at": "2025-01-26T12:00:00Z",
#             },
#         )()
#
#     def test_batch_reset_trigger_flags_initializes_flags(self) -> None:
#         """Assert the trigger signal flags are reset correctly for all apps, seeds, and thresholds"""
#         trigger_signal_flags = self.monitor._get_trigger_signal_flags()
#         # Set all flags to True first
#         for app in BettingApp.list():
#             for seed in SeedName.list():
#                 for threshold in self.monitor.THRESHOLDS:
#                     trigger_signal_flags[app][seed][threshold]["triggered"] = True
#         self.monitor._set_trigger_signal_flags(trigger_signal_flags)
#
#         self.monitor._batch_reset_trigger_flags()  # Call the reset method
#         trigger_signal_flags = self.monitor._get_trigger_signal_flags()  # Fetch the cached flags
#
#         # Assert all flags are reset to False for all apps, seeds, and thresholds
#         for app in BettingApp.list():
#             for seed in SeedName.list():
#                 for threshold in self.monitor.THRESHOLDS:
#                     self.assertFalse(trigger_signal_flags[app][seed][threshold]["triggered"])
#
#         # Assert the cache has been set correctly
#         cache_key = self.monitor.TRIGGER_CACHE_KEY
#         cached_flags = cache.get(cache_key)
#         self.assertEqual(trigger_signal_flags, cached_flags)
#
#     @patch(
#         "observers.utils.get_app_threshold_subscribers", return_value={"user1", "user2"}
#     )
#     @patch("observers.utils.OneSignal")
#     def test_process_latest_payout_triggers_notification(
#         self, mock_onesignal, mock_get_subs
#     ) -> None:
#         """Assert the notification is triggered correctly for all seeds and thresholds"""
#         for seed in SeedName.list():
#             self.mock_instance.worker.name = seed
#             self.monitor.process_latest_payout(self.mock_instance)
#             trigger_signal_flags = self.monitor._get_trigger_signal_flags()
#             for threshold in self.monitor.THRESHOLDS:
#                 if self.mock_instance.crash >= threshold:
#                     self.assertTrue(
#                         trigger_signal_flags[self.mock_instance.worker.app][seed][threshold][
#                             "triggered"
#                         ]
#                     )
#             mock_onesignal.send_push.assert_called()
#
#     @patch("observers.utils.get_app_threshold_subscribers", return_value=set())
#     @patch("observers.utils.OneSignal")
#     def test_process_latest_payout_when_no_subscribers(
#         self, mock_onesignal, mock_get_subs
#     ) -> None:
#         """Assert no notification is sent when there are no subscribers for any seed"""
#         for seed in SeedName.list():
#             self.mock_instance.worker.name = seed
#             self.monitor.process_latest_payout(self.mock_instance)
#             mock_onesignal.send_push.assert_not_called()
#
#     def test_process_latest_payout_resets_flags_when_payout_below_reset(self) -> None:
#         """Assert the flags are reset when the payout is below the reset threshold for all seeds"""
#         self.mock_instance.crash = 10  # Set payout below the reset threshold
#         self.monitor._batch_reset_trigger_flags()  # Reset all flags to False
#         trigger_signal_flags = self.monitor._get_trigger_signal_flags()
#
#         # Manually set a flag to True to test reset for all seeds
#         for seed in SeedName.list():
#             trigger_signal_flags[BettingApp.BETIKA.value][seed][self.monitor.THRESHOLDS[0]][
#                 "triggered"
#             ] = True
#         self.monitor._set_trigger_signal_flags(trigger_signal_flags)
#
#         # Call the execute method for all seeds
#         for seed in SeedName.list():
#             self.mock_instance.worker.name = seed
#             self.monitor.process_latest_payout(self.mock_instance)
#             trigger_signal_flags = self.monitor._get_trigger_signal_flags()
#             for threshold in self.monitor.THRESHOLDS:
#                 self.assertFalse(
#                     trigger_signal_flags[BettingApp.BETIKA.value][seed][threshold]["triggered"]
#                 )
