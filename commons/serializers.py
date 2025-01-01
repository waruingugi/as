from django.utils.translation import gettext_lazy as _
from phonenumbers import (
    NumberParseException,
    PhoneNumberFormat,
    PhoneNumberType,
    format_number,
    is_valid_number,
    number_type,
)
from phonenumbers import parse as parse_phone_number
from rest_framework import serializers

from commons.errors import ErrorCodes


class UserPhoneNumberField(serializers.CharField):
    default_error_messages = {"invalid": _(ErrorCodes.INVALID_PHONE_NUMBER.value)}

    def __init__(self, *args, region=None, **kwargs) -> None:
        """
        :keyword str region: 2-letter country code as defined in ISO 3166-1.
            When not supplied, defaults to :setting:`PHONENUMBER_DEFAULT_REGION`
        """
        super().__init__(*args, **kwargs)
        self.region = region or "KE"

    def to_internal_value(self, phone_number) -> str:
        """Format the phone number to international format: +254732567432"""
        PHONE_NUMBER_TYPES = (
            PhoneNumberType.MOBILE,
            PhoneNumberType.FIXED_LINE_OR_MOBILE,
        )

        try:
            phone_number = parse_phone_number(phone_number, self.region)
        except NumberParseException:
            raise serializers.ValidationError(self.error_messages["invalid"])

        if number_type(phone_number) not in PHONE_NUMBER_TYPES or not is_valid_number(
            phone_number
        ):
            raise serializers.ValidationError(self.error_messages["invalid"])

        return format_number(phone_number, PhoneNumberFormat.E164)
