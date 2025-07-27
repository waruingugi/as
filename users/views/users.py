from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from commons.pagination import StandardPageNumberPagination
from commons.permissions import IsStaffOrSelfPermission, IsStaffPermission
from observers.utils import SIGNAL_NOTIFICATION_TRIGGERS, get_app_threshold_subscribers
from users.models import SignalSetting, User
from users.serializers import (
    AppParamSerializer,
    SignalSettingSerializer,
    StaffUserCreateSerializer,
    StaffUserRetrieveUpdateSerializer,
    UserListSerializer,
    UserRetrieveUpdateSerializer,
)
from users.utils import default_signal_preference


class UserCreateView(CreateAPIView):
    """Create a user."""

    queryset = User.objects.all()
    serializer_class = StaffUserCreateSerializer
    permission_classes = [IsStaffPermission]


class UserListView(ListAPIView):
    "List users."

    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [IsStaffPermission]
    pagination_class = StandardPageNumberPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]
    search_fields = ["phone_number", "username"]
    filterset_fields = ["is_active", "is_verified", "is_staff"]
    ordering_fields = ["created_at"]


class UserRetrieveUpdateView(RetrieveUpdateAPIView):
    """Retrieve a user."""

    lookup_field = "id"
    queryset = User.objects.all()
    permission_classes = [IsStaffOrSelfPermission]

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return StaffUserRetrieveUpdateSerializer
        return UserRetrieveUpdateSerializer


class SignalSettingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    GET   /signal-settings/         → list all (staff) or current user’s own
    POST  /signal-settings/         → create-or-update for request.user
    GET   /signal-settings/{id}/    → retrieve a single record (staff only or owner)
    PUT   /signal-settings/{id}/    → update via standard update
    """

    queryset = SignalSetting.objects.all()
    serializer_class = SignalSettingSerializer
    permission_classes = [IsStaffOrSelfPermission]
    lookup_field = "id"

    def get_queryset(self):
        # staff see everyone, normal users only their own
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        If a SignalSetting for this user exists, update it;
        otherwise create it.  Returns 200 OK if update, 201 Created if new.
        """
        # 1) get or make one for this user
        instance, created = SignalSetting.objects.get_or_create(
            user=request.user,
            defaults={
                "preference": default_signal_preference()
            },  # or your default_signal_preference()
        )

        # 2) bind serializer (partial=True so missing fields aren’t required)
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True,
        )
        # 3) validate the data
        serializer.is_valid(raise_exception=True)

        # 3) run your serializer’s create/update hooks
        serializer.save(user=request.user)

        # 4) return 201 if it was new, otherwise 200
        code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=code)


class AppSubscribersView(APIView):
    permission_classes = [IsStaffPermission]

    def get(self, request, app):
        # Validate app param using AppParamSerializer
        serializer = AppParamSerializer(data={"app": app})
        serializer.is_valid(raise_exception=True)

        data = {}
        for threshold in SIGNAL_NOTIFICATION_TRIGGERS:
            subscribers = list(get_app_threshold_subscribers(app, threshold))
            data[threshold] = subscribers
        return Response({"app": app, "thresholds": data})
