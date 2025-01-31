import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status

from commons.raw_logger import logger
from notifications.constants import NotificationChannel, NotificationProvider
from notifications.models import Notification

User = get_user_model()


class OneSignalPush:
    def __init__(self) -> None:
        self.url = "https://api.onesignal.com/notifications?c=push"
        self.message = ""
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {settings.ONESIGNAL_API_KEY}",
        }
        self.user = None
        self.push_notification_name = "Majibu In-APP Push"
        self.payload = {
            "app_id": settings.ONESIGNAL_APP_ID,
            "contents": {
                "en": "",
            },
            "headings": {"en": ""},
            "name": "Majibu In-APP Push",
            "include_external_user_ids": [],
            "target_channel": "push",
            "small_icon": "ic_launcher",
        }

    def send_push(self, *, type: str, title: str, message: str, user_id: str) -> bool:
        """A code snippet in the app identifies users and sends their user_id to Onesignal.
        We then use the user_id to specify who the message is being sent to."""
        logger.info(f"Sending PUSH notification to {user_id}")
        self.payload["contents"] = {"en": message}
        self.payload["headings"] = {"en": title}
        self.payload["include_external_user_ids"] = [str(user_id)]

        try:
            user = User.objects.filter(id=user_id).first()
            self.user = user if user else self.user

            notification_obj = Notification.objects.create(
                type=type,
                message=message,
                channel=NotificationChannel.PUSH.value,
                provider=NotificationProvider.ONESIGNAL.value,
                receiving_party=user_id,
                user=self.user,
            )

            response = requests.post(self.url, json=self.payload, headers=self.headers)

            notification_obj.external_response = response.json()
            notification_obj.save()

            if response.status_code == status.HTTP_200_OK:
                logger.info(f"Push notification to {user_id} sent successfully.")
                return True

            return False

        except Exception as e:
            logger.error(f"Exception occured while sending push to {user_id}: {e}")
            return False


OneSignal = OneSignalPush()
