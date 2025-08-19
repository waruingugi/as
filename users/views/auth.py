from datetime import timedelta

from django.contrib.auth.models import update_last_login
from django.core.cache import cache
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView, GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from commons.constants import Message, PushNotification
from commons.tasks import send_push_task, send_sms_task
from commons.throttles import AuthenticationThrottle
from commons.utils import md5_hash
from notifications.constants import NotificationType
from users.models import SignalSetting, User
from users.otp import create_otp
from users.serializers import (
    OTPLoginRequestSerializer,
    OTPLoginVerifySerializer,
    OTPVerificationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ResendOTPVerificationSerializer,
    UserCreateSerializer,
    UserTokenObtainPairSerializer,
)
from users.utils import default_signal_preference


@extend_schema(tags=["auth"])
class UserTokenObtainPairView(TokenObtainPairView):
    serializer_class = UserTokenObtainPairSerializer


@extend_schema(tags=["auth"])
class RegisterView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    throttle_classes = [AuthenticationThrottle]
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        password = validated_data.pop("password")
        user = serializer.save()

        # Set the hashed password
        user.set_password(password)
        user.save()

        phone_number = str(user.phone_number)
        otp = create_otp(phone_number)

        message = Message.OTP_SMS.value.format(otp)
        send_sms_task.delay(
            phone_number=phone_number, type=NotificationType.OTP.value, message=message
        )

        # Send Push Notification Welcome Message
        # send_push_task.delay(
        #     notification_type=NotificationType.MARKETING.value,
        #     title=PushNotification.WELCOME_MESSAGE.title,
        #     message=PushNotification.WELCOME_MESSAGE.message,
        #     user_ids=[user.id],
        # )

        # Create default signal settings for the user
        SignalSetting.objects.create(user=user, preference=default_signal_preference())

        return user


@extend_schema(tags=["auth"])
class ResendOTPVerificationView(GenericAPIView):
    serializer_class = ResendOTPVerificationSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthenticationThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]
            otp = create_otp(phone_number)

            message = Message.OTP_SMS.value.format(otp)
            send_sms_task.delay(
                phone_number=phone_number,
                type=NotificationType.OTP.value,
                message=message,
            )

            return Response(
                {"detail": "OTP sent successfully"}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["auth"])
class OTPVerificationView(GenericAPIView):
    serializer_class = OTPVerificationSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthenticationThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]

            # Activate user
            user = User.objects.get(phone_number=phone_number)
            user.is_verified = True
            user.save()

            # Clear OTP from cache
            cache.delete(md5_hash(phone_number))

            return Response(
                {"detail": "User activated successfully."}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["auth"])
class PasswordResetRequestView(GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]

            # De-verify user. OTP will be sent to re-verify
            user = User.objects.get(phone_number=phone_number)
            user.is_verified = False
            user.save()

            otp = create_otp(phone_number)

            message = Message.OTP_SMS.value.format(otp)
            send_sms_task.delay(
                phone_number=phone_number,
                type=NotificationType.OTP.value,
                message=message,
            )

            return Response(
                {"detail": "OTP has been sent to your phone number."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["auth"])
class PasswordResetConfirmView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data["phone_number"]
            user = User.objects.get(phone_number=phone_number)
            user.set_password(serializer.validated_data["new_password"])

            # Once an OTP is confirmed, the user is verified
            user.is_verified = True
            user.save()

            # Clear OTP from cache
            cache.delete(md5_hash(phone_number))

            return Response(
                {"detail": "Password has been reset successfully."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=["auth"])
class OTPLoginRequestView(GenericAPIView):
    """
    POST { phone_number }
    - Get or create user (with unusable password)
    - Send OTP via SMS
    """

    permission_classes = [AllowAny]
    serializer_class = OTPLoginRequestSerializer
    throttle_classes = [AuthenticationThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data["phone_number"]

        user, created = User.objects.get_or_create(
            phone_number=phone_number,
            defaults={
                "is_active": True,
                "is_verified": False,
            },
        )

        if created:
            # Make sure the account has no valid password by default for OTP-only flow
            user.set_unusable_password()
            user.save()

            # Create default signal settings & send welcome push (consistent with RegisterView)
            SignalSetting.objects.create(
                user=user, preference=default_signal_preference()
            )

            # Schedule the push notification to be sent after 5 minutes
            send_push_task.apply_async(
                kwargs={
                    "notification_type": NotificationType.MARKETING.value,
                    "title": PushNotification.WELCOME_MESSAGE.title,
                    "message": PushNotification.WELCOME_MESSAGE.message,
                    "user_ids": [user.id],
                },
                eta=timezone.now() + timedelta(minutes=5),
            )

        # Generate and send OTP
        otp = create_otp(str(phone_number))
        message = Message.OTP_SMS.value.format(otp)
        send_sms_task.delay(
            phone_number=str(phone_number),
            type=NotificationType.OTP.value,
            message=message,
        )

        return Response(
            {
                "detail": "OTP sent successfully.",
                "is_new_user": created,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(tags=["auth"])
class OTPLoginVerifyView(GenericAPIView):
    """
    POST { phone_number, otp }
    - Validate OTP
    - Mark user verified (if not)
    - Return JWT (refresh, access, exp, user_id)
    """

    permission_classes = [AllowAny]
    serializer_class = OTPLoginVerifySerializer
    throttle_classes = [AuthenticationThrottle]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data["phone_number"]
        user = User.objects.get(phone_number=phone_number)

        # Consider OTP login as verification
        if not user.is_verified:
            user.is_verified = True
            user.save()

        # Issue tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token
        data = {
            "refresh": str(refresh),
            "access": str(access),
            "exp": access["exp"],  # unix timestamp
            "user_id": refresh["user_id"],
        }

        update_last_login(None, user)

        # Clear OTP from cache
        cache.delete(md5_hash(str(phone_number)))

        return Response(data, status=status.HTTP_200_OK)
