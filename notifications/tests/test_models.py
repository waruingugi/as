from commons.constants import Message
from commons.tests.test_base import UserBaseAPITestCase
from notifications.constants import (
    NotificationChannel,
    NotificationProvider,
    NotificationType,
)
from notifications.models import Notification


class NotificationModelTestCase(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.notification = Notification.objects.create(
            type=NotificationType.OTP.value,
            message=Message.OTP_SMS.value.format("4578"),
            channel=NotificationChannel.SMS.value,
            provider=NotificationProvider.HOSTPINNACLESMS.value,
            receiving_party=str(self.user.phone_number),
            user=self.user,
        )

    def test_notification_creates_model_instances_successfully(self) -> None:
        notification = self.notification
        self.assertTrue(isinstance(notification, Notification))
        self.assertEqual(
            str(notification), f"{notification.type} - {notification.message}"
        )
        self.assertEqual(notification.type, NotificationType.OTP.value)
        self.assertEqual(notification.message, Message.OTP_SMS.value.format("4578"))
        self.assertEqual(notification.channel, NotificationChannel.SMS.value)
        self.assertEqual(
            notification.provider, NotificationProvider.HOSTPINNACLESMS.value
        )
        self.assertEqual(notification.receiving_party, str(self.user.phone_number))
        self.assertEqual(notification.user, self.user)
        self.assertFalse(notification.is_read)
