from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from commons.tests.test_base import UserBaseAPITestCase
from commons.throttles import AuthenticationThrottle
from users.models import User
from users.otp import create_otp


class RegisterViewTestCase(APITestCase):
    @patch("users.views.auth.send_push_task.delay")
    @patch("users.views.auth.send_sms_task.delay")
    def test_view_creates_user(self, send_sms_mock, _) -> None:
        """Assert registration view creates user."""
        data = {
            "phone_number": "+254701456761",
            "password": "passwordAl123",
            "is_staff": True,
        }

        response = self.client.post(reverse("auth:register"), data)

        self.assertEqual(
            response.status_code, 201
        )  # Check if user was created successfully
        self.assertTrue(
            User.objects.filter(phone_number="+254701456761").exists()
        )  # Check if user exists

        send_sms_mock.assert_called_once()  # Check if send_sms was called

        # Check if the correct arguments were passed to send_sms
        phone_number = send_sms_mock.call_args.kwargs["phone_number"]

        self.assertTrue(response.data["is_active"])
        self.assertFalse(response.data["is_verified"])
        self.assertNotIn("password", response.data)
        self.assertNotIn("is_staff", response.data)
        user = User.objects.get(phone_number=data["phone_number"])

        # Assert that the password is not stored as plain text
        self.assertNotEqual(user.password, data["password"])
        self.assertFalse(user.is_staff)
        self.assertEqual(phone_number, "+254701456761")

    @patch("users.views.auth.send_push_task.delay")
    @patch("users.views.auth.send_sms_task.delay")
    def test_view_creates_user_with_national_phone_number(
        self, send_sms_mock, _
    ) -> None:
        """Assert registration view creates user with national number."""
        data = {"phone_number": "0701686761", "password": "passwordAl123"}

        response = self.client.post(reverse("auth:register"), data)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(phone_number="+254701686761").exists())

    @patch("users.views.auth.send_push_task.delay")
    @patch("users.views.auth.send_sms_task.delay")
    def test_view_throttles_requests(self, send_sms_mock, _):
        """Assert the view throttles requests."""
        data = {"phone_number": "+254701451731", "password": "passwordAl123"}
        for _ in range(10):
            self.client.post(reverse("auth:register"), data)

        # Check that some requests are throttled (HTTP 429 Too Many Requests)
        throttled_response = self.client.post(reverse("auth:register"), data)
        self.assertEqual(
            throttled_response.status_code, status.HTTP_429_TOO_MANY_REQUESTS
        )

        # Clear the throttle cache
        AuthenticationThrottle.cache.clear()

    @patch("users.views.auth.send_push_task.delay")
    @patch("users.views.auth.send_sms_task.delay")
    def test_default_signals_setting_created_on_registration(
        self, send_sms_mock, _
    ) -> None:
        """Assert default signals setting is created on user registration."""
        data = {"phone_number": "+254701234567", "password": "passwordAl123"}
        response = self.client.post(reverse("auth:register"), data)

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(phone_number=data["phone_number"])
        self.assertIsNotNone(
            user.signal_settings
        )  # Check if default signals setting exists


class AuthTokenTestCase(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            phone_number="+254701456761", password="StrongPassword123", is_active=True
        )
        self.user.is_verified = True
        self.user.save()

    def test_url_obtains_token_pair_successfully(self) -> None:
        """Assert endpoint returns access and refresh token."""
        url = reverse("auth:obtain-token")
        data = {"phone_number": self.user.phone_number, "password": "StrongPassword123"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user_id", response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        self.access_token = response.data["access"]  # Don't remove this line
        self.refresh_token = response.data["refresh"]  # Don't remove this line

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_url_obtains_token_pair_using_national_number(self) -> None:
        """Assert endpoint standardizes phone number to required format."""
        url = reverse("auth:obtain-token")
        data = {"phone_number": "0701456761", "password": "StrongPassword123"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_url_refreshes_token_successfully(self):
        """Verify that the new access token is different from the old one"""
        # First, obtain a token pair
        self.test_url_obtains_token_pair_successfully()

        url = reverse("auth:refresh-token")
        data = {"refresh": self.refresh_token}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        new_access_token = response.data["access"]
        self.assertNotEqual(self.access_token, new_access_token)

    def test_access_denied_if_user_is_inactive(self):
        """Assert inactive user is denied login access."""
        User.objects.create_user(
            phone_number="+254701436763", password="StrongPassword123", is_active=False
        )
        data = {"phone_number": "+254701436763", "password": "StrongPassword123"}

        response = self.client.post(reverse("auth:obtain-token"), data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "This account has been deactivated. Please contact support.",
        )

    def test_access_denied_if_user_is_not_verified(self):
        """Assert inactive user is denied login access."""
        user = User.objects.create_user(
            phone_number="+254701436763", password="StrongPassword123", is_active=False
        )
        user.is_active = True
        user.is_verified = True
        user.save()
        data = {"phone_number": "+254701436763", "password": "StrongPassword123"}

        # Assert active and verified user gains access
        response = self.client.post(reverse("auth:obtain-token"), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert active but unverified user is denied access
        user.is_verified = False
        user.save()
        response = self.client.post(reverse("auth:obtain-token"), data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_denied_if_wrong_password_entered(self) -> None:
        """Assert user is denied access if wrong password is entered."""
        data = {"phone_number": "+254701456761", "password": "wrong_password"}
        response = self.client.post(reverse("auth:obtain-token"), data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "The phone number or password is incorrect. Please try again.",
        )


class OTPVerificationTestCase(APITestCase):
    def setUp(self) -> None:
        self.phone_number = "+254701476761"
        self.user = User.objects.create_user(
            phone_number=self.phone_number,
            password="strong_password",
        )
        self.otp = create_otp(self.phone_number)
        self.url = reverse("auth:verify-otp")

    def test_otp_verifies_user(self) -> None:
        """Assert OTP verifies user."""
        data = {"phone_number": self.phone_number, "otp": self.otp}
        response = self.client.post(self.url, data)
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["detail"], "User activated successfully.")
        self.assertTrue(self.user.is_verified)

    def test_invalid_otp_verification_fails(self):
        """"""
        data = {"phone_number": self.phone_number, "otp": "invalid_otp"}
        response = self.client.post(self.url, data)
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("otp", response.data)
        self.assertFalse(self.user.is_verified)


class ResendOTPVerificationTestCase(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.user.is_verified = False
        self.user.save()

        self.url = reverse("auth:resend-otp")
        self.data = {"phone_number": str(self.user.phone_number)}

    @patch("users.views.auth.send_push_task.delay")
    @patch("users.views.auth.create_otp")
    @patch("users.views.auth.send_sms_task.delay")
    def test_throttling(self, mock_send_sms, mock_create_otp, _) -> None:
        for _ in range(20):  # Assuming throttle limit is 5 requests per hour
            response = self.client.post(self.url, self.data, format="json")

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        AuthenticationThrottle.cache.clear()

    @patch("users.views.auth.send_push_task.delay")
    @patch("users.views.auth.create_otp")
    @patch("users.views.auth.send_sms_task.delay")
    def test_user_is_already_verified(self, mock_send_sms, mock_create_otp, _) -> None:
        self.user.is_verified = True
        self.user.save()

        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("users.views.auth.send_push_task.delay")
    @patch("users.views.auth.create_otp")
    @patch("users.views.auth.send_sms_task.delay")
    def test_user_does_not_exist(self, mock_send_sms, mock_create_otp, _):
        data = {"phone_number": "+254711111111"}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PasswordResetTestCase(APITestCase):
    def setUp(self):
        self.phone_number = "+254701234567"
        self.user = User.objects.create_user(
            phone_number=self.phone_number, password="StrongPassword123"
        )
        self.user.is_verified = True
        self.user.save()

        self.password_reset_url = reverse("auth:password-reset-request")
        self.password_reset_confirm_url = reverse("auth:password-reset-confirm")

    @patch("users.views.auth.send_push_task.delay")
    @patch("users.views.auth.send_sms_task.delay")
    def test_view_sends_otp(self, send_sms_mock, _):
        """Assert view sends OTP to validate user"""
        response = self.client.post(
            self.password_reset_url, {"phone_number": self.user.phone_number}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        send_sms_mock.assert_called_once()
        self.assertEqual(
            response.data["detail"], "OTP has been sent to your phone number."
        )

    def test_view_resets_password(self):
        """Assert the updates the password"""
        new_password = "NewStrongPassword123"
        otp = create_otp(self.phone_number)

        response = self.client.post(
            self.password_reset_confirm_url,
            {
                "phone_number": "0701234567",
                "otp": otp,
                "new_password": new_password,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that the password has actually been changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

        # Assert that the user is verified
        self.assertTrue(self.user.is_verified)

    def test_view_fails_to_reset_password(self):
        """Assert view fails to reset the password if OTP is invalid."""
        new_password = "NewStrongPassword123"

        response = self.client.post(
            self.password_reset_confirm_url,
            {
                "phone_number": self.phone_number,
                "otp": "wrong_otp",
                "new_password": new_password,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
