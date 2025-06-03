import uuid
from unittest.mock import Mock, patch

from commons.constants import Message, PushNotification
from commons.tests.test_base import UserBaseAPITestCase
from notifications.constants import NotificationChannel, NotificationType
from notifications.models import Notification
from notifications.push import OneSignal
from notifications.sms import HostPinnacleSMS


class OneSignalPushTest(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.push_service = OneSignal

    @patch("notifications.push.requests.Session.post")
    def test_send_push_success(self, mock_post_request) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post_request.return_value = mock_response

        result = self.push_service.send_push(
            notification_type=NotificationType.MARKETING.value,
            title=PushNotification.WELCOME_MESSAGE.title,
            message=PushNotification.WELCOME_MESSAGE.message,
            user_ids=[str(self.user.id)],
        )

        self.assertTrue(result)
        mock_post_request.assert_called_once()
        notification = Notification.objects.get(user=self.user)
        self.assertEqual(notification.message, PushNotification.WELCOME_MESSAGE.message)
        self.assertEqual(notification.type, NotificationType.MARKETING.value)
        self.assertEqual(notification.channel, NotificationChannel.PUSH.value)

    @patch("notifications.push.requests.Session.post")
    def test_send_push_failure(self, mock_post_request) -> None:
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"status": "error"}
        mock_post_request.return_value = mock_response

        result = self.push_service.send_push(
            notification_type=NotificationType.MARKETING.value,
            title=PushNotification.WELCOME_MESSAGE.title,
            message=PushNotification.WELCOME_MESSAGE.message,
            user_ids=[str(self.user.id)],
        )

        self.assertFalse(result)
        mock_post_request.assert_called_once()
        notification = Notification.objects.get(user=self.user)
        self.assertEqual(notification.message, PushNotification.WELCOME_MESSAGE.message)
        self.assertEqual(notification.type, NotificationType.MARKETING.value)
        self.assertEqual(notification.channel, NotificationChannel.PUSH.value)

    @patch("notifications.push.requests.Session.post")
    def test_send_push_no_users(self, mock_post_request) -> None:
        # Use a user ID that does not exist
        result = self.push_service.send_push(
            notification_type=NotificationType.MARKETING.value,
            title=PushNotification.WELCOME_MESSAGE.title,
            message=PushNotification.WELCOME_MESSAGE.message,
            user_ids=[str(uuid.uuid4())],
        )
        self.assertFalse(result)
        mock_post_request.assert_not_called()

    @patch("notifications.push.requests.Session.post")
    def test_send_push_exception(self, mock_post_request) -> None:
        mock_post_request.side_effect = Exception("Network error")
        result = self.push_service.send_push(
            notification_type=NotificationType.MARKETING.value,
            title=PushNotification.WELCOME_MESSAGE.title,
            message=PushNotification.WELCOME_MESSAGE.message,
            user_ids=[str(self.user.id)],
        )
        self.assertFalse(result)
        mock_post_request.assert_called_once()


# class OneSignalPushTest(UserBaseAPITestCase):
#     def setUp(self) -> None:
#         self.user = self.create_user()
#         self.push_service = OneSignal
#
#     @patch("notifications.push.requests.post")
#     def test_send_push_success(self, mock_post_request) -> None:
#         mock_response = Mock()
#         mock_response.status_code = 200
#         mock_response.json.return_value = {"status": "success"}
#         mock_post_request.return_value = mock_response
#
#         result = self.push_service.send_push(
#             type=NotificationType.MARKETING.value,
#             title=PushNotification.WELCOME_MESSAGE.title,
#             message=PushNotification.WELCOME_MESSAGE.message,
#             user_id=str(self.user.id),
#         )
#
#         self.assertTrue(result)
#         mock_post_request.assert_called_once_with(
#             self.push_service.url,
#             json=self.push_service.payload,
#             headers=self.push_service.headers,
#         )
#
#         notification = Notification.objects.get(user=self.user)
#         self.assertEqual(notification.message, PushNotification.WELCOME_MESSAGE.message)
#
#     @patch("notifications.push.requests.post")
#     def test_send_push_failure(self, mock_post_request) -> None:
#         mock_response = Mock()
#         mock_response.status_code = 400
#         mock_response.json.return_value = {"status": "error"}
#         mock_post_request.return_value = mock_response
#
#         result = self.push_service.send_push(
#             type=NotificationType.MARKETING.value,
#             title=PushNotification.WELCOME_MESSAGE.title,
#             message=PushNotification.WELCOME_MESSAGE.message,
#             user_id=str(self.user.id),
#         )
#
#         self.assertFalse(result)
#         mock_post_request.assert_called_once_with(
#             self.push_service.url,
#             json=self.push_service.payload,
#             headers=self.push_service.headers,
#         )
#
#         notification = Notification.objects.get(user=self.user)
#         self.assertEqual(notification.message, PushNotification.WELCOME_MESSAGE.message)


class HostPinnacleTest(UserBaseAPITestCase):
    def setUp(self) -> None:
        self.user = self.create_user()
        self.sms_service = HostPinnacleSMS

    @patch("notifications.sms.requests.post")
    def test_send_sms_success(self, mock_post_request) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post_request.return_value = mock_response

        result = self.sms_service.send_sms(
            phone_number=str(self.user.phone_number),
            type=NotificationType.OTP.value,
            message=Message.OTP_SMS.value,
        )

        self.assertTrue(result)
        mock_post_request.assert_called_once()

    @patch("notifications.sms.requests.post")
    def test_send_sms_failure(self, mock_post_request) -> None:
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"status": "error"}
        mock_post_request.return_value = mock_response

        result = self.sms_service.send_sms(
            phone_number=str(self.user.phone_number),
            type=NotificationType.OTP.value,
            message=Message.OTP_SMS.value,
        )

        self.assertFalse(result)
        mock_post_request.assert_called_once()

    @patch("notifications.sms.requests.post")
    def test_send_sms_exception(self, mock_post_request) -> None:
        mock_post_request.side_effect = Exception("Network error")

        result = self.sms_service.send_sms(
            phone_number=str(self.user.phone_number),
            type=NotificationType.OTP.value,
            message=Message.OTP_SMS.value,
        )
        self.assertFalse(result)
        mock_post_request.assert_called_once()
