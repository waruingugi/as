from unittest.mock import patch

from django.test import TestCase

from users.utils import default_signal_preference


class TestGenerateDefaultSignalPref(TestCase):
    @patch("commons.constants.BettingApp.list")
    def test_generate_default_signal_pref(self, mock_betting_app_list) -> None:
        # Mock the list of betting apps
        mock_betting_app_list.return_value = ["App1", "App2", "App3"]

        # Call the function
        result = default_signal_preference()

        # Expected result
        expected_result = {
            "App1": {"subscribed": False},
            "App2": {"subscribed": False},
            "App3": {"subscribed": False},
        }

        # Assertions
        self.assertEqual(result, expected_result)
        mock_betting_app_list.assert_called_once()
