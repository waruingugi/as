from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from commons.constants import BettingApp
from commons.errors import ErrorCodes
from commons.serializers import UserPhoneNumberField
from users.constants import TOTP_LENGTH
from users.models import SignalSetting, User
from users.utils import default_signal_preference
from users.validators import (
    OTPValidator,
    PhoneNumberExistsValidator,
    PhoneNumberIsAvailableValidator,
    UsernameValidator,
)


class UserTokenObtainPairSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "invalid_credentials": _(
            "The phone number or password is incorrect. Please try again."
        ),
        "inactive_account": _(ErrorCodes.DEACTIVATED_USER.value),
        "unverified_account": _(
            "This account is not verified. Please contact support."
        ),
    }

    def validate(self, attrs):
        phone_field = UserPhoneNumberField()
        phone_number = phone_field.to_internal_value(attrs.get(self.username_field))
        password = attrs.get("password")

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            raise AuthenticationFailed(
                self.error_messages["invalid_credentials"], code="invalid_credentials"
            )

        if not user.check_password(password):
            raise AuthenticationFailed(
                self.error_messages["invalid_credentials"], code="invalid_credentials"
            )

        if not user.is_active:
            raise AuthenticationFailed(
                self.error_messages["inactive_account"], code="inactive_account"
            )

        if not user.is_verified:
            raise AuthenticationFailed(
                self.error_messages["unverified_account"], code="unverified_account"
            )

        # All checks passed — call super().validate to generate tokens
        attrs[self.username_field] = phone_number
        data = super().validate(attrs)

        token = self.get_token(self.user)
        data["refresh"] = str(token)
        data["access"] = str(token.access_token)
        data["exp"] = token.payload["exp"]
        data["user_id"] = token.payload["user_id"]

        update_last_login(None, self.user)

        return data


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


class ResendOTPVerificationSerializer(serializers.Serializer):
    phone_number = UserPhoneNumberField(
        required=True, validators=[PhoneNumberExistsValidator()]
    )

    def validate(self, data):
        user = User.objects.get(phone_number=data["phone_number"])
        if not user.is_active:
            raise serializers.ValidationError(ErrorCodes.DEACTIVATED_USER.value)
        return data


class OTPVerificationSerializer(serializers.Serializer):
    phone_number = UserPhoneNumberField(
        required=True, validators=[PhoneNumberExistsValidator()]
    )
    otp = serializers.CharField(required=True, max_length=TOTP_LENGTH)

    def validate(self, data):
        OTPValidator.validate_otp(
            phone_number=data.get("phone_number"), otp_code=data.get("otp")
        )
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    phone_number = UserPhoneNumberField(
        required=True, validators=[PhoneNumberExistsValidator()]
    )


class PasswordResetConfirmSerializer(serializers.Serializer):
    phone_number = UserPhoneNumberField(
        required=True, validators=[PhoneNumberExistsValidator()]
    )
    otp = serializers.CharField(required=True)
    new_password = serializers.CharField(
        required=True, write_only=True, validators=[validate_password]
    )

    def validate(self, data):
        OTPValidator.validate_otp(
            phone_number=data.get("phone_number"), otp_code=data.get("otp")
        )
        return data


class SignalSettingSerializer(serializers.ModelSerializer):
    preference = serializers.DictField(
        child=serializers.DictField(
            child=serializers.BooleanField(), allow_empty=False
        ),
        required=True,
    )

    class Meta:
        model = SignalSetting
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "user")

    def validate_preference(self, value):
        valid_apps = set(BettingApp.list())
        for app, cfg in value.items():
            if app not in valid_apps:
                raise serializers.ValidationError(f"Invalid app: {app}")
            if not isinstance(cfg, dict) or set(cfg.keys()) != {"subscribed"}:
                raise serializers.ValidationError(
                    f"Preference for {app} must only contain 'subscribed' key"
                )
            if not isinstance(cfg.get("subscribed"), bool):
                raise serializers.ValidationError(
                    f"'subscribed' for {app} must be a boolean"
                )
        return value

    def _normalize_preferences(self, existing_prefs, incoming_prefs) -> dict:
        """
        Ensures only one app can have its `subscribed` field set to True.
        """
        valid_apps = set(BettingApp.list())
        incoming_prefs = {
            app: cfg for app, cfg in incoming_prefs.items() if app in valid_apps
        }

        normalized_preferences = {
            app: existing_prefs.get(app, {}).copy()
            for app in set(existing_prefs) | set(incoming_prefs)
        }
        for app, cfg in incoming_prefs.items():
            normalized_preferences[app].update(cfg)

        # Only one app can be subscribed
        newly_on = [app for app, cfg in incoming_prefs.items() if cfg.get("subscribed")]

        if newly_on:
            keep = newly_on[-1]
            for app in normalized_preferences:
                normalized_preferences[app]["subscribed"] = app == keep
        else:
            # If no new subscription, keep existing state
            for app, cfg in normalized_preferences.items():
                if "subscribed" not in cfg:
                    cfg["subscribed"] = False

        return normalized_preferences

    def create(self, validated_data):
        prefs = validated_data.get("preference", {}) or {}
        validated_data["preference"] = self._normalize_preferences(
            existing_prefs=default_signal_preference(),
            incoming_prefs=prefs,
        )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "preference" in validated_data:
            incoming = validated_data["preference"] or {}
            validated_data["preference"] = self._normalize_preferences(
                existing_prefs=instance.preference or {}, incoming_prefs=incoming
            )
        return super().update(instance, validated_data)


class AppParamSerializer(serializers.Serializer):
    app = serializers.ChoiceField(choices=BettingApp.list())


class OTPLoginRequestSerializer(serializers.Serializer):
    """Accepts phone number only; we do NOT require the user to exist."""

    phone_number = UserPhoneNumberField(required=True)


class OTPLoginVerifySerializer(serializers.Serializer):
    """Validates phone + OTP (reuses your OTP validation)."""

    default_error_messages = {
        "inactive_account": _(ErrorCodes.DEACTIVATED_USER.value),
        "invalid_credentials": _(
            "The phone number or OTP is incorrect. Please try again."
        ),
    }

    phone_number = UserPhoneNumberField(required=True)
    otp = serializers.CharField(required=True, max_length=TOTP_LENGTH)

    def validate_phone_number(self, value):
        """Validates that the phone number exists and is active."""
        try:
            user = User.objects.get(phone_number=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                self.error_messages["invalid_credentials"], code="invalid_credentials"
            )

        if not user.is_active:
            raise serializers.ValidationError(
                self.error_messages["inactive_account"], code="inactive_account"
            )

        return value

    def validate(self, attrs):
        """Validates the OTP against the provided phone number."""
        OTPValidator.validate_otp(
            phone_number=attrs.get("phone_number"), otp_code=attrs.get("otp")
        )
        return attrs
