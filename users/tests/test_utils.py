from unittest.mock import MagicMock, patch

from django.test import TestCase

from commons.constants import SIGNAL_NOTIFICATION_TRIGGERS, CacheKeys
from users.utils import UserSignalSettingsCacheManager, default_signal_preference


class TestGenerateDefaultSignalPref(TestCase):
    @patch("commons.constants.BettingApp.list")
    def test_generate_default_signal_pref(self, mock_betting_app_list) -> None:
        # Mock the list of betting apps
        mock_betting_app_list.return_value = ["App1", "App2", "App3"]

        # Call the function
        result = default_signal_preference()

        # Expected result
        expected_result = {
            "App1": {"subscribed": False, "trigger": None},
            "App2": {"subscribed": False, "trigger": None},
            "App3": {"subscribed": False, "trigger": None},
        }

        # Assertions
        self.assertEqual(result, expected_result)
        mock_betting_app_list.assert_called_once()


class TestUserSignalSettingsCacheManager(TestCase):
    def setUp(self) -> None:
        self.mock_instance = MagicMock()
        self.mock_instance.user_id = 1
        self.trigger1 = SIGNAL_NOTIFICATION_TRIGGERS[0]
        self.trigger2 = SIGNAL_NOTIFICATION_TRIGGERS[1]
        self.mock_instance.preference = {
            "app1": {"subscribed": True, "trigger": self.trigger1},
            "app2": {"subscribed": False, "trigger": self.trigger2},
        }

        self.mock_cache_data = {
            "app1": {self.trigger1: {1}},
            "app2": {self.trigger2: {1}},
        }

    @patch("users.utils.cache")
    @patch("users.utils.BettingApp.list", return_value=["app1", "app2", "app3"])
    def test_update(self, mock_betting_app_list, mock_cache) -> None:
        mock_cache.get.return_value = self.mock_cache_data

        UserSignalSettingsCacheManager.update(self.mock_instance)

        mock_cache.set.assert_called_once_with(
            CacheKeys.USERS_SIGNAL_SETTINGS,
            {
                "app1": {self.trigger1: {1}},
                "app2": {self.trigger2: set()},
            },
            timeout=60 * 60 * 24,
        )

    @patch("users.utils.cache")
    @patch("users.utils.BettingApp.list", return_value=["app1", "app2", "app3"])
    def test_remove_invalid_preferences(
        self, mock_betting_app_list, mock_cache
    ) -> None:
        mock_cache.get.return_value = self.mock_cache_data
        manager = UserSignalSettingsCacheManager(self.mock_instance)

        manager._remove_invalid_preferences()

        self.assertIn(1, manager.users_signal_prefs["app1"][self.trigger1])
        self.assertNotIn(1, manager.users_signal_prefs["app2"][self.trigger2])

    @patch("users.utils.cache")
    @patch("users.utils.BettingApp.list", return_value=["app1", "app2", "app3"])
    def test_add_valid_preferences(self, mock_betting_app_list, mock_cache) -> None:
        mock_cache.get.return_value = self.mock_cache_data
        manager = UserSignalSettingsCacheManager(self.mock_instance)

        manager._add_valid_preferences()

        self.assertIn(1, manager.users_signal_prefs["app1"][self.trigger1])
        self.assertIn(1, manager.users_signal_prefs["app2"][self.trigger2])
