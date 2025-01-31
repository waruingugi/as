import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from phonenumbers import parse
from rest_framework import status

from commons.raw_logger import logger

User = get_user_model


class SMSProvider:
    """Abstract class for SMS providers."""

    priority: int  # Lower priority value = higher precedence

    def send_sms(self, phone_number: str, message: str, type: str) -> bool:
        """Simulate sending an SMS. Returns True if successful, False otherwise."""
        raise NotImplementedError


class HostPinnacle(SMSProvider):
    priority = 1

    def __init__(self) -> None:
        self.url = "https://smsportal.hostpinnacle.co.ke/SMSApi/send"
        self.user = None
        self.headers: dict[str, str] = {}
        self.sms_payload = {
            "userid": settings.HOST_PINNACLE_USER_ID,
            "password": settings.HOST_PINNACLE_PASSWORD,
            "mobile": "",
            "senderid": settings.HOST_PINNACLE_SENDER_ID,
            "msg": "",
            "sendMethod": "quick",
            "msgType": "text",
            "output": "json",
            "duplicatecheck": "true",
        }
        self.files: list = []

    def format_phone_number(self, phone) -> str:
        """
        HostPinnacle requires numbers without a leading + sign.
        Example: 254704302356
        """
        parsed_phone = parse(phone)
        return f"{parsed_phone.country_code}{parsed_phone.national_number}"

    def send_sms(self, *, phone_number: str, type: str, message: str) -> bool:
        logger.info(f"Sending {type} SMS to {phone_number}...")
        self.sms_payload["mobile"] = self.format_phone_number(phone_number)
        self.sms_payload["msg"] = message

        try:
            response = requests.post(
                self.url, headers=self.headers, data=self.sms_payload, files=self.files
            )

            if response.status_code == status.HTTP_200_OK:
                logger.info(f"SMS to {phone_number} sent successfully.")
                return True

            return False

        except Exception as e:
            logger.error(f"Exception occured while sending SMS to {phone_number}: {e}")
            return False


HostPinnacleSMS = HostPinnacle()
