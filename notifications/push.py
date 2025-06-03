import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status

from commons.raw_logger import logger
from notifications.constants import NotificationChannel
from notifications.models import Notification

User = get_user_model()


class OneSignalPush:
    URL = "https://api.onesignal.com/notifications?c=push"
    TIMEOUT = 60 * 5  # 5 minutes
    HEADERS = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {settings.ONESIGNAL_API_KEY}",
    }

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def send_push(
        self, *, notification_type: str, title: str, message: str, user_ids: list[str]
    ) -> bool:
        """
        Send a push notification to one or more users
        :param notification_type: The type of notification
        :param title: The title of the notification
        :param message: The message to be sent
        :param user_ids: The user ID(s) to send the notification to
        """
        user_ids_list = [str(uid) for uid in user_ids]  # Normalize user IDs to strings
        logger.info(f"Sending PUSH notification to {user_ids_list}")

        # Fetch valid users
        users = list(User.objects.filter(id__in=user_ids).values("id", "phone_number"))

        if not users:
            logger.warning(f"No users found for push title: {title}")
            return False

        # Prepare payload
        payload = {
            "app_id": settings.ONESIGNAL_APP_ID,
            "contents": {"en": message},
            "headings": {"en": title},
            "include_external_user_ids": user_ids_list,
            "target_channel": "push",
            "small_icon": "ic_launcher",
            "priority": 10,  # High priority
            "ttl": self.TIMEOUT,  # Time to live
        }

        # Create notifications in bulk
        notifications = [
            Notification(
                type=notification_type,
                message=message,
                channel=NotificationChannel.PUSH.value,
                receiving_party=user["phone_number"],
                user_id=user["id"],
            )
            for user in users
        ]
        Notification.objects.bulk_create(notifications)

        try:
            response = self.session.post(self.URL, json=payload)
            response_json = response.json()
            # Update the notification objects with the response
            for notif in notifications:
                notif.external_response = response_json
            Notification.objects.bulk_update(notifications, ["external_response"])

            if response.status_code == status.HTTP_200_OK:
                logger.info(f"Push notification to {user_ids_list} sent successfully.")
                return True

            logger.error(f"Failed to send push notification: {response_json}")
            return False

        except Exception as e:
            logger.error(
                f"Exception occurred while sending push to {user_ids_list}: {e}"
            )
            return False

    #
    # def __init__(self) -> None:
    #     self.url = "https://api.onesignal.com/notifications?c=push"
    #     self.message = ""
    #     self.headers = {
    #         "Content-Type": "application/json",
    #         "Authorization": f"Basic {settings.ONESIGNAL_API_KEY}",
    #     }
    #     self.timeout = 60 * 5  # 5 minutes
    #     self.user = None
    #     self.push_notification_name = "Majibu In-APP Push"
    #     self.payload = {
    #         "app_id": settings.ONESIGNAL_APP_ID,
    #         "contents": {
    #             "en": "",
    #         },
    #         "headings": {"en": ""},
    #         "name": "Majibu In-APP Push",
    #         "include_external_user_ids": [],
    #         "target_channel": "push",
    #         "small_icon": "ic_launcher",
    #         "priority": 10,  # High priority
    #         "ttl": self.timeout,  # Time to live
    #     }

    # def send_push(self, *, type: str, title: str, message: str, user_id: str) -> bool:
    #     """A code snippet in the app identifies users and sends their user_id to Onesignal.
    #     We then use the user_id to specify who the message is being sent to."""
    #     logger.info(f"Sending PUSH notification to {user_id}")
    #     self.payload["contents"] = {"en": message}
    #     self.payload["headings"] = {"en": title}
    #     self.payload["include_external_user_ids"] = [str(user_id)]
    #
    #     try:
    #         user = User.objects.filter(id=user_id).first()
    #         self.user = user if user else self.user
    #
    #         notification_obj = Notification.objects.create(
    #             type=type,
    #             message=message,
    #             channel=NotificationChannel.PUSH.value,
    #             provider=NotificationProvider.ONESIGNAL.value,
    #             receiving_party=user.phone_number,
    #             user=self.user,
    #         )
    #
    #         response = requests.post(self.url, json=self.payload, headers=self.headers)
    #
    #         notification_obj.external_response = response.json()
    #         notification_obj.save()
    #
    #         if response.status_code == status.HTTP_200_OK:
    #             logger.info(f"Push notification to {user_id} sent successfully.")
    #             return True
    #
    #         return False
    #
    #     except Exception as e:
    #         logger.error(f"Exception occurred while sending push to {user_id}: {e}")
    #         return False


OneSignal = OneSignalPush()
