from collections import defaultdict
from unittest.mock import MagicMock, patch

from django.test import TestCase

from commons.constants import CacheKeys
from commons.tasks import refresh_users_signal_settings


class TestRefreshUsersSignalSettings(TestCase):
    @patch("commons.tasks.SignalSetting.objects.select_related")
    @patch("commons.tasks.BettingApp.list")
    @patch("commons.tasks.cache.set")
    def test_refresh_users_signal_settings(
        self, mock_cache_set, mock_betting_app_list, mock_select_related
    ) -> None:
        # Mock betting apps
        mock_betting_app_list.return_value = ["BETGR8", "BETMAX"]

        # Mock signal settings
        mock_signal_setting = MagicMock()
        mock_signal_setting.preference = {
            "BETGR8": {"subscribed": True, "trigger": 90},
            "INVALID_APP": {"subscribed": True, "trigger": 90},
        }
        mock_signal_setting.user_id = "user-123"
        mock_select_related.return_value.only.return_value = [mock_signal_setting]

        # Call the task
        refresh_users_signal_settings()

        # Validate preferences were updated
        self.assertEqual(
            mock_signal_setting.preference,
            {"BETGR8": {"subscribed": True, "trigger": 90}},
        )
        mock_signal_setting.save.assert_called_once_with(update_fields=["preference"])

        # Validate cache was updated
        expected_cache_data = defaultdict(lambda: defaultdict(set))
        expected_cache_data["BETGR8"][90].add("user-123")
        mock_cache_set.assert_called_once_with(
            CacheKeys.USERS_SIGNAL_SETTINGS, expected_cache_data, timeout=60 * 60 * 24
        )
