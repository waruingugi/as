from uuid import uuid4

from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import User

# from django.conf import settings


class UserBaseAPITestCase(APITestCase):
    phone_number = "+254712345678"
    password = uuid4().hex
    username = "testuser"
    staff_username = "admin"
    staff_phone_number = "0701234567"
    staff_password = uuid4().hex

    def create_user(self) -> User:
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            phone_number=self.phone_number,
        )
        return self.user

    def create_foreign_user(self) -> User:
        self.foreign_user = User.objects.create_user(
            phone_number="+254713476781", password="password456", username="testuser2"
        )
        return self.foreign_user

    def create_staff_user(self) -> User:
        self.staff_user = User.objects.create_user(
            phone_number=self.staff_phone_number,
            username=self.staff_username,
            password=self.staff_password,
            is_staff=True,
        )
        return self.staff_user

    def force_authenticate_user(self) -> None:
        self.client = APIClient()
        if not hasattr(self, "user"):
            self.user = self.create_user()

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def force_authenticate_staff_user(self) -> None:
        if not hasattr(self, "staff_user"):
            self.create_staff_user()

        self.client = APIClient()
        self.client.force_authenticate(user=self.staff_user)

    def create_access_token(self, user) -> str:
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)  # type: ignore
