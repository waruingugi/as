from commons.constants import SMSProvider
from commons.logger import logger


class NotificationFacade:
    """Facade for sending notifications (SMS, Push, Email)."""

    MAX_RETRIES = 2  # Maximum retries per provider

    def send_sms(self, phone_number: str, message: str, provider, type: str):
        """Send SMS, retrying each provider up to MAX_RETRIES times before failing over."""
        if provider:
            return self._attempt_with_retries(provider, phone_number, message, type)

        # Default: Try all providers in order of priority
        for sms_provider in SMSProvider.list():
            if self._attempt_with_retries(sms_provider, phone_number, message, type):
                return True

        logger.warning("All SMS providers failed.")
        return False

    def _attempt_with_retries(
        self, provider, phone_number: str, message: str, type: str
    ) -> bool:
        """Attempt sending SMS, retrying if necessary."""
        for attempt in range(1, self.MAX_RETRIES + 1):
            logger.info(f"Attempt {attempt} using {provider.__class__.__name__}...")
            if provider.send_sms(phone_number=phone_number, message=message, type=type):
                logger.info(
                    f"Success with {provider.__class__.__name__} on attempt {attempt}"
                )
                return True
        logger.warning(
            f"Provider {provider.__class__.__name__} failed after {self.MAX_RETRIES} retries."
        )
        return False


Notification = NotificationFacade()
