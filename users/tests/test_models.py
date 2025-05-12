from uuid import uuid4

from django.test import TestCase

from commons.constants import User
from users.models import SignalSetting


class UserModelTests(TestCase):
    def setUp(self) -> None:
        """Set up test data."""
        self.test_phone_number = "+254701301401"
        self.test_password = uuid4().hex
        self.test_username = "testuser"
        self.user = User.objects.create_user(
            phone_number=self.test_phone_number,
            password=self.test_password,
            username=self.test_username,
        )

    def test_create_user(self) -> None:
        """Assert fields created have the same value as those passed."""

        self.assertEqual(self.user.phone_number, self.test_phone_number)
        self.assertTrue(self.user.check_password(self.test_password))
        self.assertEqual(self.user.username, self.test_username)
        self.assertFalse(self.user.is_verified)
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)

    def test_phone_number_is_unique(self) -> None:
        """Assert phone number is unique for all users."""

        with self.assertRaises(Exception):
            User.objects.create_user(
                phone_number=self.test_phone_number,
                password=uuid4().hex,
                username="testuser1",
            )

    def test_username_is_unique(self) -> None:
        """Assert username is unique for all users."""

        with self.assertRaises(Exception):
            User.objects.create_user(
                phone_number="+254701301405",
                password=uuid4().hex,
                username=self.test_username,
            )

    def test_username_is_generated_if_not_set(self) -> None:
        """Assert username is generated if not set."""

        user = User.objects.create_user(
            phone_number="+254701301405",
            password=uuid4().hex,
        )

        self.assertIsNotNone(user.username)
        self.assertNotEqual(user.username, "")
        self.assertIsInstance(user.username, str)


class SignalSettingModelTests(TestCase):
    def setUp(self) -> None:
        """Set up test data."""
        self.user = User.objects.create_user(
            phone_number="+254701301401",
            password=uuid4().hex,
            username="testuser",
        )
        self.signal_setting = SignalSetting.objects.create(user=self.user)

    def test_signal_setting_creation(self) -> None:
        """Test that a SignalSetting instance is created correctly."""
        self.assertEqual(self.signal_setting.user, self.user)
        self.assertIsNone(self.signal_setting.preference)

    def test_signal_setting_str_representation(self) -> None:
        """Test the string representation of the SignalSetting model."""
        self.assertEqual(
            str(self.signal_setting), f"{self.user} - {self.signal_setting.preference}"
        )
