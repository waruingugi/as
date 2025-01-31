from unittest.mock import patch

from django.test import TestCase

from commons.constants import NotificationType, SMSProvider
from notifications.base import Notification


class TestNotification(TestCase):
    @patch("notifications.sms.HostPinnacle.send_sms", side_effect=[False, True])
    def test_send_sms_with_retry(self, mock_send):
        """Test that SMS is retried before failing."""
        result = Notification.send_sms(
            "+254712345678",
            "Retry message",
            SMSProvider.HostPinnacle.value,
            NotificationType.MARKETING.value,
        )

        self.assertTrue(result)
        self.assertEqual(mock_send.call_count, 2)  # Number of retries

    @patch("notifications.sms.HostPinnacle.send_sms", return_value=True)
    def test_send_sms_specific_provider(self, mock_send) -> None:
        """Test that a specific provider is used if specified."""
        result = Notification.send_sms(
            "+254712345678",
            "Test with specific provider",
            SMSProvider.HostPinnacle.value,
            NotificationType.MARKETING.value,
        )

        self.assertTrue(result)
        mock_send.assert_called_once()
