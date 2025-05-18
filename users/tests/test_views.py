from django.core.cache import cache
from django.urls import reverse
from rest_framework import status

from commons.constants import BettingApp, CacheKeys
from commons.tests.test_base import UserBaseAPITestCase
from users.constants import MAX_USERNAME_LEN, MIN_USERNAME_LEN
from users.models import SignalSetting, User
from users.utils import default_signal_preference


class UserCreateViewTests(UserBaseAPITestCase):
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


class UserRetrieveUpdateViewTests(UserBaseAPITestCase):
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


# Add these tests to your test file


class SignalSettingViewSetTests(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.staff_user = self.create_staff_user()
        self.signal_setting = SignalSetting.objects.create(
            user=self.user, preference=default_signal_preference()
        )

        self.APP0, self.APP1 = BettingApp.list()[0], BettingApp.list()[1]

        self.url = reverse("users:signal-settings")
        self.detail_url = reverse(
            "users:signal-settings-detail", kwargs={"id": self.signal_setting.id}
        )

    def test_staff_can_view_all_signal_settings(self) -> None:
        """Assert staff users can view all SignalSettings."""
        self.force_authenticate_staff_user()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], SignalSetting.objects.count())

    def test_user_can_view_own_signal_settings(self) -> None:
        """Assert regular users can only view their own SignalSettings."""
        self.force_authenticate_user()
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"][0]["id"], str(self.signal_setting.id))

    def test_user_cannot_view_others_signal_settings(self) -> None:
        """Assert regular users cannot view SignalSettings of other users."""
        foreign_user = self.create_foreign_user()
        self.client.force_authenticate(user=foreign_user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_staff_can_view_specific_signal_setting(self) -> None:
        """Assert staff users can view any specific SignalSetting."""
        self.force_authenticate_user()
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.signal_setting.id))

    def test_user_can_view_own_specific_signal_setting(self) -> None:
        """Assert regular users can view their own specific SignalSetting."""
        self.force_authenticate_user()
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(self.signal_setting.id))

    def test_user_can_create_signal_setting(self) -> None:
        """Assert regular users can create their own SignalSetting."""
        cache.delete(CacheKeys.USERS_SIGNAL_SETTINGS)  # Clear specific cache
        SignalSetting.objects.filter(
            user=self.user
        ).delete()  # Ensure no existing settings
        self.force_authenticate_user()

        preference = default_signal_preference()
        preference[self.APP1]["subscribed"] = True
        preference[self.APP1]["trigger"] = 90
        data = {"preference": preference}
        response = self.client.post(self.url, data, format="json")

        # Assert setting is saved to cache
        cached_data = cache.get(CacheKeys.USERS_SIGNAL_SETTINGS)
        self.assertIn(str(self.user.id), cached_data[self.APP1][90])

        # Assert response is correct
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"], self.user.id)
        self.assertEqual(response.data["preference"], preference)

    def test_user_can_update_own_signal_preference(self) -> None:
        """Assert regular users can update their own SignalSetting preference."""
        self.force_authenticate_user()
        data = {"preference": {self.APP1: {"subscribed": True, "trigger": 80}}}
        response = self.client.put(self.detail_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.signal_setting.refresh_from_db()
        self.assertTrue(self.signal_setting.preference[self.APP1]["subscribed"])

        # Assert setting is saved to cache
        cached_data = cache.get(CacheKeys.USERS_SIGNAL_SETTINGS)
        self.assertIn(str(self.user.id), cached_data[self.APP1][80])

    def test_user_cannot_update_others_signal_preference(self) -> None:
        """Assert regular users cannot update the SignalSetting preference of other users."""
        foreign_user = self.create_foreign_user()
        self.client.force_authenticate(user=foreign_user)
        data = {"preference": {self.APP1: {"subscribed": True, "trigger": 90}}}
        response = self.client.put(self.detail_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_only_have_one_subscription_on_creation(self) -> None:
        """Assert can only have one app subscription set to True on post"""
        self.force_authenticate_user()
        SignalSetting.objects.all().delete()  # Clear previous settings
        data = {
            "preference": {
                self.APP0: {"subscribed": True, "trigger": 90},
                self.APP1: {"subscribed": True, "trigger": 80},
            }
        }
        response = self.client.post(self.url, data, format="json")
        signal_setting = SignalSetting.objects.get(user=self.user)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(signal_setting.preference[self.APP0]["subscribed"], False)
        self.assertEqual(signal_setting.preference[self.APP1]["subscribed"], True)

    def test_user_can_only_have_one_subscription_on_update(self) -> None:
        """Assert can only have one app subscription set to True on put"""
        self.force_authenticate_user()
        data = {
            "preference": {
                self.APP0: {"subscribed": True, "trigger": 90},
                self.APP1: {"subscribed": True, "trigger": 80},
            }
        }
        response = self.client.put(self.detail_url, data, format="json")
        signal_setting = SignalSetting.objects.get(user=self.user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(signal_setting.preference[self.APP0]["subscribed"], False)
        self.assertEqual(signal_setting.preference[self.APP1]["subscribed"], True)

    def test_invalid_apps_are_ignored(self) -> None:
        """Assert invalid apps are ignored on update"""
        self.force_authenticate_user()
        preference = default_signal_preference()
        preference["invalid_app"] = {"subscribed": True, "trigger": 90}

        data = {
            "preference": {
                "invalid_app": {"subscribed": True, "trigger": 80},
            }
        }

        response = self.client.put(self.detail_url, data, format="json")
        signal_setting = SignalSetting.objects.get(user=self.user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("invalid_app", signal_setting.preference)
        self.assertNotIn("invalid_app", cache.get(CacheKeys.USERS_SIGNAL_SETTINGS))
