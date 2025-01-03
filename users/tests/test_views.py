from django.urls import reverse
from rest_framework import status

from commons.tests.test_base import UserBaseAPITestCase
from users.constants import MAX_USERNAME_LEN, MIN_USERNAME_LEN
from users.models import User


class UserCreateAPIViewTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.create_url = reverse("users:create")
        self.data = {
            "phone_number": "0703245678",
            "username": "stacy",
            "password": "passwordAl123",
        }
        self.force_authenticate_staff_user()

    def test_staff_user_creates_user_successfully(self) -> None:
        """Assert endpoint creates user successfully."""

        response = self.client.post(self.create_url, self.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertIn("phone_number", response.data)
        self.assertIn("username", response.data)
        self.assertFalse(response.data["is_verified"])
        self.assertFalse(response.data["is_active"])
        user = User.objects.get(username=self.data["username"])

        # Assert that the password is not stored as plain text
        self.assertNotEqual(user.password, self.data["password"])

    def test_view_generates_default_username(self) -> None:
        """Assert a default username is generated if the field is not defined."""
        data = {"phone_number": "0703245674", "password": "password124"}
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data["username"])

    def test_view_fails_if_username_is_too_long(self) -> None:
        """Assert username does not exceed maximum string length."""
        username = "a" * (MAX_USERNAME_LEN + 1)
        data = {
            "phone_number": "0703245674",
            "username": username,
            "password": "password124",
        }
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_view_fails_if_username_is_too_short(self) -> None:
        """Assert username is not below minimum string length."""
        username = "a" * (MIN_USERNAME_LEN - 1)
        data = {
            "phone_number": "0703245674",
            "username": username,
            "password": "password124",
        }
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_view_fails_if_username_has_special_characters(self) -> None:
        """Assert username is not below minimum string length."""
        username = "testuser*"
        data = {
            "phone_number": "0703245674",
            "username": username,
            "password": "password124",
        }
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_view_fails_if_phone_number_field_is_missing(self) -> None:
        """Assert validation error is raised if phone number field is missing."""
        data = {
            "password": "password123",
        }
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data)

    def test_view_fails_if_phone_number_is_not_valid(self) -> None:
        """Assert validation error is raised if phone number is invalid."""
        data = {"phone_number": "070324", "password": "password124"}
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_normal_user_fails_to_create_user(self) -> None:
        """Assert normal users do not have permission to create users."""
        self.force_authenticate_user()
        response = self.client.post(self.create_url, self.data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserRetrieveUpdateAPIViewTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.foreign_user = self.create_foreign_user()

        self.force_authenticate_user()
        self.detail_url = reverse("users:detail", kwargs={"id": self.user.id})

    def test_user_can_not_update_read_only_fields(self) -> None:
        """Assert the phone number field can not be edited."""
        data = {
            "phone_number": self.user.phone,
            "is_staff": True,
            "is_active": False,
            "is_verified": True,
        }
        response = self.client.put(self.detail_url, data)

        self.user.refresh_from_db()
        self.assertEqual(self.user.phone, data["phone_number"])
        self.assertFalse(response.data["is_verified"])
        self.assertFalse(response.data["is_staff"])
        self.assertTrue(response.data["is_active"])

    def test_user_can_edit_their_profile(self) -> None:
        """Assert a user can edit themselves."""
        data = {"username": "activerodent"}

        self.force_authenticate_user()
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "activerodent")

    def test_staff_can_edit_other_users(self) -> None:
        """Assert a staff user can edit other users.."""
        data = {
            "is_active": False,
            "is_verified": False,
        }
        self.force_authenticate_staff_user()
        response = self.client.put(self.detail_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.is_active, False)

    def test_user_can_update_username_field(self) -> None:
        """Assert user can update their own username"""
        data = {"username": "foreignuser"}
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "foreignuser")

    def test_view_fails_to_update_if_username_exists(self) -> None:
        """Assert updating to username that exists fails."""
        prev_username = self.user.username
        User.objects.create_user(
            phone_number="+254703456785",
            password="password455",
            username="testuser5",
        )
        # Case sensitive search
        data = {"username": "testuser5"}
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Case insensitive search
        data = {"username": "TestUser5"}
        response = self.client.put(self.detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()
        self.assertEqual(self.user.username, prev_username)

    def test_view_retrieves_user_data(self) -> None:
        """Assert expected fields are returned in detail view."""
        response = self.client.put(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id", response.data)
        self.assertIn("phone_number", response.data)
        self.assertIn("username", response.data)
        self.assertIn("is_verified", response.data)
        self.assertIn("is_active", response.data)
        self.assertIn("is_staff", response.data)

    def test_user_can_only_retrieve_their_own_data(self) -> None:
        """Assert user can only view their own data."""
        self.detail_url = reverse("users:detail", kwargs={"id": self.foreign_user.id})
        response = self.client.put(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UserListAPIViewTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.user1 = User.objects.create_user(
            phone_number="+254703456785", password="password123", username="testuser1"
        )
        self.user2 = User.objects.create_user(
            phone_number="+254703456781", password="password456", username="testuser2"
        )
        self.list_url = reverse("users:list")

        self.force_authenticate_staff_user()

    def test_view_returns_list_of_users(self) -> None:
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], User.objects.count())

    # TODO: Uncomment below code once Bearer auth is implemented
    # def test_normal_user_can_not_list_users(self) -> None:
    #     client = APIClient()
    #     access_token = self.create_access_token(self.user1)
    #     client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

    #     response = client.get(self.list_url)
    #     self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
