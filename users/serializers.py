from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from commons.serializers import UserPhoneNumberField
from users.models import User
from users.validators import PhoneNumberIsAvailableValidator, UsernameValidator


class BaseUserCreateSerializer(serializers.ModelSerializer):
    phone_number = UserPhoneNumberField(
        required=True, validators=[PhoneNumberIsAvailableValidator()]
    )
    username = serializers.CharField(required=False, validators=[UsernameValidator()])
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],  # Use Django's built-in validators
    )

    class Meta:
        model = User


class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = [
            "id",
            "username",
            "phone_number",
            "password",
            "is_active",
            "is_verified",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "username": {"read_only": True},
            "is_active": {"read_only": True},
            "is_verified": {"read_only": True},
            "password": {"write_only": True},
        }


class StaffUserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = [
            "id",
            "created_at",
            "updated_at",
            "username",
            "phone_number",
            "password",
            "is_active",
            "is_verified",
            "is_staff",
        ]
        extra_kwargs = {
            "id": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        # Extract password and hash it
        password = validated_data.pop("password", None)
        user = self.Meta.model(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user


class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "username",
            "phone_number",
        ]


class BaseUserDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False, validators=[UsernameValidator()])

    class Meta:
        model = User
        fields = [
            "id",
            "created_at",
            "updated_at",
            "username",
            "phone_number",
            "is_active",
            "is_verified",
            "is_staff",
        ]


class UserRetrieveUpdateSerializer(BaseUserDetailSerializer):
    class Meta(BaseUserDetailSerializer.Meta):
        read_only_fields = (
            "id",
            "created_at",
            "updated_at",
            "is_active",
            "phone_number",
            "is_verified",
            "is_staff",
        )


class StaffUserRetrieveUpdateSerializer(BaseUserDetailSerializer):
    class Meta(BaseUserDetailSerializer.Meta):
        """Staff can edit any of the fields except those specified below."""

        read_only_fields = ("id", "created_at", "updated_at", "phone_number")


class UserListSerializer(BaseUserDetailSerializer):
    class Meta(BaseUserDetailSerializer.Meta):
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "username",
            "phone_number",
            "is_active",
            "is_verified",
            "is_staff",
        ]
