import unittest
from unittest.mock import patch

from users.utils import default_signal_preference


class TestGenerateDefaultSignalPref(unittest.TestCase):
    @patch("commons.constants.BettingApp.list")
    def test_generate_default_signal_pref(self, mock_betting_app_list) -> None:
        # Mock the list of betting apps
        mock_betting_app_list.return_value = ["App1", "App2", "App3"]

        # Call the function
        result = default_signal_preference()

        # Expected result
        expected_result = {
            "App1": {"subscribed": False, "probability": None},
            "App2": {"subscribed": False, "probability": None},
            "App3": {"subscribed": False, "probability": None},
        }

        # Assertions
        self.assertEqual(result, expected_result)
        mock_betting_app_list.assert_called_once()
