from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveUpdateAPIView

from commons.pagination import StandardPageNumberPagination
from commons.permissions import IsStaffPermission
from workers.models import Worker
from workers.serializers import (
    WorkerCreateSerializer,
    WorkerListSerializer,
    WorkerUpdateSerializer,
)


class WorkerCreateView(CreateAPIView):
    queryset = Worker.objects.all()
    serializer_class = WorkerCreateSerializer
    permission_classes = [IsStaffPermission]


class WorkerListView(ListAPIView):
    queryset = Worker.objects.all()
    serializer_class = WorkerListSerializer
    permission_classes = [IsStaffPermission]
    pagination_class = StandardPageNumberPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]
    search_fields = ["name", "app"]
    ordering_fields = ["created_at"]


class WorkerRetrieveUpdateView(RetrieveUpdateAPIView):
    lookup_field = "id"
    queryset = Worker.objects.all()
    serializer_class = WorkerUpdateSerializer
    permission_classes = [IsStaffPermission]
