from typing import Any

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from random_username.generate import generate_username

from commons.models import Base
from users.constants import MAX_USERNAME_LEN, MIN_USERNAME_LEN


def username_generator(
    minimum_length=MIN_USERNAME_LEN, max_length=MAX_USERNAME_LEN
) -> str:
    """Generate default username."""
    username = generate_username(1)[0]
    while (
        len(username) > max_length
        or len(username) < minimum_length
        or User.objects.filter(username=username).exists()
    ):
        username = generate_username(1)[0]

    return username


class UserManager(BaseUserManager):
    def create_user(
        self,
        *,
        phone_number: PhoneNumberField,
        password: str,
        **extra_fields: Any,
    ) -> "User":
        if not phone_number:
            raise ValueError("The Phone number field must be set")

        user = self.model(phone_number=phone_number, **extra_fields)
        user.set_password(password)  # type: ignore
        user.save(using=self.db)

        return user  # type: ignore

    def create_superuser(
        self, *, phone_number: PhoneNumberField, password: str, **extra_fields: Any
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True."))
        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(
            phone_number=phone_number, password=password, **extra_fields
        )


class User(AbstractBaseUser, PermissionsMixin, Base):
    """The default user model"""

    username = models.CharField(
        max_length=255, default=username_generator, unique=True, null=True
    )
    phone_number = PhoneNumberField(blank=False, unique=True)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD: str = "phone_number"
    REQUIRED_FIELDS: list[str] = []  # type: ignore

    def __str__(self) -> str:
        return str(self.phone_number)

    @property
    def phone(self) -> str:
        return str(self.phone_number)

    class Meta:
        ordering = ("-created_at",)
