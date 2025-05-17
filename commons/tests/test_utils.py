from unittest.mock import MagicMock, patch

from django.test import TestCase

from commons.constants import SIGNAL_NOTIFICATION_TRIGGERS, CacheKeys
from commons.utils import UserSignalSettingsCacheManager


class TestUserSignalSettingsCacheManager(TestCase):
    def setUp(self) -> None:
        self.mock_instance = MagicMock()
        self.user_id1, self.user_id2 = "1", "2"
        self.mock_instance.user_id = self.user_id1
        self.trigger1 = SIGNAL_NOTIFICATION_TRIGGERS[0]
        self.trigger2 = SIGNAL_NOTIFICATION_TRIGGERS[1]
        self.mock_instance.preference = {
            "app1": {"subscribed": True, "trigger": self.trigger1},
            "app2": {"subscribed": False, "trigger": self.trigger2},
        }

        self.mock_cache_data = {
            "app1": {self.trigger1: {self.user_id1}},
            "app2": {self.trigger2: {self.user_id1}},
        }

    @patch("commons.utils.cache")
    @patch("commons.utils.BettingApp.list", return_value=["app1", "app2", "app3"])
    def test_update(self, mock_betting_app_list, mock_cache) -> None:
        mock_cache.get.return_value = self.mock_cache_data

        UserSignalSettingsCacheManager.update(self.mock_instance)

        mock_cache.set.assert_called_once_with(
            CacheKeys.USERS_SIGNAL_SETTINGS,
            {
                "app1": {self.trigger1: {self.user_id1}},
                "app2": {self.trigger2: set()},
            },
            timeout=60 * 60 * 24,
        )

    @patch("commons.utils.cache")
    @patch("commons.utils.BettingApp.list", return_value=["app1", "app2", "app3"])
    def test_remove_invalid_preferences(
        self, mock_betting_app_list, mock_cache
    ) -> None:
        mock_cache.get.return_value = self.mock_cache_data
        manager = UserSignalSettingsCacheManager(self.mock_instance)

        manager._remove_invalid_preferences()

        self.assertIn(self.user_id1, manager.users_signal_prefs["app1"][self.trigger1])
        self.assertNotIn(
            self.user_id1, manager.users_signal_prefs["app2"][self.trigger2]
        )

    @patch("commons.utils.cache")
    @patch("commons.utils.BettingApp.list", return_value=["app1", "app2", "app3"])
    def test_add_valid_preferences(self, mock_betting_app_list, mock_cache) -> None:
        mock_cache.get.return_value = self.mock_cache_data
        manager = UserSignalSettingsCacheManager(self.mock_instance)

        manager._add_valid_preferences()

        self.assertIn(self.user_id1, manager.users_signal_prefs["app1"][self.trigger1])
        self.assertIn(self.user_id1, manager.users_signal_prefs["app2"][self.trigger2])

    @patch("commons.utils.cache")
    @patch("commons.utils.BettingApp.list", return_value=["app1", "app2", "app3"])
    @patch("commons.utils.SignalSetting.objects.select_related")
    def test_reload_cache(
        self, mock_select_related, mock_betting_app_list, mock_cache
    ) -> None:
        """
        Test the `_reload_cache` functionality to ensure the entire cache is refreshed for all users.
        """
        mock_cache.get.return_value = self.mock_cache_data

        # Mock signal settings for multiple users
        mock_signal_setting_1 = MagicMock()
        mock_signal_setting_1.preference = {
            "app1": {"subscribed": True, "trigger": self.trigger1},
            "app2": {"subscribed": False, "trigger": self.trigger2},
        }
        mock_signal_setting_1.user_id = 1

        mock_signal_setting_2 = MagicMock()
        mock_signal_setting_2.preference = {
            "app1": {"subscribed": True, "trigger": self.trigger1},
            "app3": {"subscribed": True, "trigger": self.trigger2},
        }
        mock_signal_setting_2.user_id = self.user_id2

        mock_select_related.return_value.only.return_value = [
            mock_signal_setting_1,
            mock_signal_setting_2,
        ]

        manager = UserSignalSettingsCacheManager()
        manager._refresh_cache()

        # Validate the cache was updated correctly for all users
        mock_cache.set.assert_called_once_with(
            CacheKeys.USERS_SIGNAL_SETTINGS,
            {
                "app1": {self.trigger1: {self.user_id1, self.user_id2}},
                "app2": {self.trigger2: set()},
                "app3": {self.trigger2: {self.user_id2}},
            },
            timeout=60 * 60 * 24,
        )
