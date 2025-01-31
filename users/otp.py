import json
from typing import Dict
from uuid import uuid4

import pyotp
from django.core.cache import cache

from commons.raw_logger import logger
from commons.utils import md5_hash
from users.constants import TOTP_EXPIRY_TIME, TOTP_LENGTH


class TOTP:
    @staticmethod
    def create(
        secret: str,
        length: int = TOTP_LENGTH,
        interval: int = TOTP_EXPIRY_TIME,
    ) -> str:
        """
        Creates a new time otp based on a shared secret
        length - Number of digits on the otp
        interval - lifetime of the otp
        """

        totp = pyotp.TOTP(s=secret, digits=length, interval=interval)
        return totp.now()

    @staticmethod
    def verify(
        otp: str,
        secret: str,
        length: int = TOTP_LENGTH,
        interval: int = TOTP_EXPIRY_TIME,
    ) -> bool:
        """
        Verifies the OTP passed in against the current time OTP.
        """

        totp = pyotp.TOTP(s=secret, digits=length, interval=interval)
        return totp.verify(otp)

    @staticmethod
    def secret() -> str:
        """Generate a random secret."""

        return pyotp.random_base32()


def create_otp(phone_number: str) -> str:
    """Create One Time Password for user"""
    totp_data: Dict[str, str] = {
        "totp_id": str(uuid4()),
        "secret": TOTP.secret(),
    }
    cache.set(md5_hash(phone_number), json.dumps(totp_data), timeout=TOTP_EXPIRY_TIME)
    logger.info(f"Created OTP to validate {phone_number}.")

    return TOTP.create(totp_data["secret"], TOTP_LENGTH, TOTP_EXPIRY_TIME)


def validate_otp(otp: str, phone_number: str) -> bool:
    """Validate OTP submitted by user"""
    user_otp_data = cache.get(md5_hash(phone_number))

    if user_otp_data is not None:
        totp_data = json.loads(user_otp_data)

        return TOTP.verify(
            otp=otp,
            secret=totp_data["secret"],
        )

    return False
