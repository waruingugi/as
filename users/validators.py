from rest_framework import serializers

from commons.errors import ErrorCodes
from users.constants import MAX_USERNAME_LEN, MIN_USERNAME_LEN
from users.models import User
from users.otp import validate_otp


class PhoneNumberIsAvailableValidator:
    def __call__(self, phone) -> None:
        if User.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError(ErrorCodes.PHONE_NUMBER_EXISTS.value)


class UsernameValidator:
    def __init__(
        self, minimum_length=MIN_USERNAME_LEN, max_length=MAX_USERNAME_LEN
    ) -> None:
        self.max_len = max_length
        self.min_len = minimum_length

    def __call__(self, username) -> None:
        if len(username) < self.min_len:
            raise serializers.ValidationError(ErrorCodes.USERNAME_IS_TOO_SHORT.value)

        if len(username) > self.max_len:
            raise serializers.ValidationError(ErrorCodes.USERNAME_IS_TOO_LONG.value)

        if not username.isalnum():
            raise serializers.ValidationError(ErrorCodes.USERNAME_IS_INVALID.value)

        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError(ErrorCodes.USERNAME_EXISTS.value)


class PhoneNumberExistsValidator:
    def __call__(self, phone_number) -> None:
        if not User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError(ErrorCodes.USER_DOES_NOT_EXIST.value)


class OTPValidator:
    @staticmethod
    def validate_otp(phone_number: str, otp_code: str) -> None:
        if not validate_otp(otp_code, phone_number):
            raise serializers.ValidationError(ErrorCodes.INVALID_OTP.value)
