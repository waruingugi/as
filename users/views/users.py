from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from commons.pagination import StandardPageNumberPagination
from commons.permissions import IsStaffOrSelfPermission, IsStaffPermission
from users.models import SignalSetting, User
from users.serializers import (
    SignalSettingSerializer,
    StaffUserCreateSerializer,
    StaffUserRetrieveUpdateSerializer,
    UserListSerializer,
    UserRetrieveUpdateSerializer,
)


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


class SignalSettingViewSet(ModelViewSet):
    """
    ViewSet for SignalSetting model.
    """

    queryset = SignalSetting.objects.all()
    serializer_class = SignalSettingSerializer
    permission_classes = [IsStaffOrSelfPermission]
    lookup_field = "id"

    def get_queryset(self):
        # Staff can view all SignalSettings
        if self.request.user.is_staff:
            return self.queryset
        # Regular users can only view their own SignalSetting
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Override the create to associate the SignalSetting with the requesting user."""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Override the update to handle create if instance being updated does not exist."""
        try:
            # 1) Try to fetch the existing object once (very efficient)
            instance = self.get_object()
            is_create = False
        except Http404:
            instance = None
            is_create = True

        # 2) Bind serializer: pass instance if updating, or None to create
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=kwargs.get("partial", False),
        )
        serializer.is_valid(raise_exception=True)

        # 3) serializer.save(...) will call create() or update() in your serializer
        serializer.save(user=request.user)

        # 4) Pick status code based on whether we created it
        code = status.HTTP_201_CREATED if is_create else status.HTTP_200_OK
        return Response(serializer.data, status=code)
