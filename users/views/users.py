from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveUpdateAPIView

from commons.pagination import StandardPageNumberPagination
from commons.permissions import IsStaffOrSelfPermission, IsStaffPermission
from users.models import User
from users.serializers import (
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
