from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from commons.pagination import StandardPageNumberPagination
from commons.permissions import IsStaffPermission
from commons.utils import get_worker_health
from workers.filters import WorkerFilter
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
    filterset_class = WorkerFilter
    search_fields = ["name"]
    ordering_fields = ["created_at"]


class WorkerRetrieveUpdateView(RetrieveUpdateAPIView):
    lookup_field = "id"
    queryset = Worker.objects.all()
    serializer_class = WorkerUpdateSerializer
    permission_classes = [IsStaffPermission]


class WorkerDeleteView(DestroyAPIView):
    lookup_field = "id"
    queryset = Worker.objects.all()
    serializer_class = WorkerUpdateSerializer
    permission_classes = [IsStaffPermission]


class WorkersHealthView(APIView):
    serializer_class = None

    def get(self, request, app: str):
        """Custom API view that returns the health status of the workers in an app."""
        workers = Worker.objects.filter(app=app)
        if workers.exists():
            data = []
            for worker in workers:
                worker_is_healthy = get_worker_health(str(worker.id))
                worker_status = "ok" if worker_is_healthy else "error"

                data.append(
                    {
                        "app": app,
                        "id": worker.id,
                        "name": worker.name,
                        "status": worker_status,
                    }
                )

            return Response(data, status=status.HTTP_200_OK)

        return Response(
            {"detail": "No workers found"}, status=status.HTTP_404_NOT_FOUND
        )
