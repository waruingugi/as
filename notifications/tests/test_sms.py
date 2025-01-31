from unittest.mock import patch

from django.test import TestCase

from notifications.constants import NotificationType
from notifications.sms import HostPinnacle


class TestHostPinnacleSMS(TestCase):
    @patch("notifications.sms.requests.post")  # Mock HTTP request
    def test_send_sms_success(self, mock_post) -> None:
        """Test that SMS is sent successfully."""
        mock_post.return_value.status_code = 200  # Simulate success response

        provider = HostPinnacle()
        success = provider.send_sms(
            phone_number="+254712345678",
            type=NotificationType.MARKETING.value,
            message="Test message",
        )

        self.assertTrue(success)
        mock_post.assert_called_once()

    @patch("notifications.sms.requests.post")
    def test_send_sms_failure(self, mock_post) -> None:
        """Test that SMS sending fails if API returns error."""
        mock_post.return_value.status_code = 500  # Simulate API failure

        provider = HostPinnacle()
        success = provider.send_sms(
            phone_number="+254712345678",
            type=NotificationType.MARKETING.value,
            message="Test failure",
        )

        self.assertFalse(success)
        mock_post.assert_called_once()

    def test_format_phone_number(self) -> None:
        """Test that phone numbers are formatted correctly."""
        provider = HostPinnacle()
        formatted = provider.format_phone_number("+254712345678")
        self.assertEqual(formatted, "254712345678")  # Expected format
