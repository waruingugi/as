from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView, GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from commons.constants import Message, PushNotification
from commons.tasks import send_push_task, send_sms_task
from commons.throttles import AuthenticationThrottle
from commons.utils import md5_hash
from notifications.constants import NotificationType
from users.models import User
from users.otp import create_otp
from users.serializers import (
    OTPVerificationSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ResendOTPVerificationSerializer,
    UserCreateSerializer,
    UserTokenObtainPairSerializer,
)


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
        send_push_task.delay(
            type=NotificationType.MARKETING.value,
            title=PushNotification.WELCOME_MESSAGE.title,
            message=PushNotification.WELCOME_MESSAGE.message,
            user_id=user.id,
        )

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

            user.is_active = True  # Make the user active if necessary
            user.save()

            # Clear OTP from cache
            cache.delete(md5_hash(phone_number))

            return Response(
                {"detail": "Password has been reset successfully."},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
