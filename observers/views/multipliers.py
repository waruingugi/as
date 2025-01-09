from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import CreateAPIView, ListAPIView

from commons.errors import ErrorCodes
from commons.pagination import StandardPageNumberPagination
from commons.permissions import IsStaffPermission
from observers.models import Multiplier
from observers.serializers import MultiplierCreateSerializer, MultiplierReadSerializer
from observers.utils import get_new_multipliers
from workers.models import Worker


class MultiplierCreateView(CreateAPIView):
    serializer_class = MultiplierCreateSerializer
    authentication_classes = []

    def perform_create(self, serializer):
        # Get API key from the header
        api_key = self.request.headers.get("API-KEY")
        if not api_key:
            raise AuthenticationFailed(ErrorCodes.WORKER_API_KEY_IS_REQUIRED.value)

        # Authenticate the worker
        worker = get_object_or_404(Worker, key=api_key)
        multipliers_list = serializer.validated_data["multipliers"]

        # Reverse the multipliers_list because the last element is the earliest payout
        new_multipliers = get_new_multipliers(worker.id, multipliers_list)
        new_multipliers.reverse()

        multipliers = [
            Multiplier(worker=worker, crash=crash) for crash in new_multipliers
        ]
        Multiplier.objects.bulk_create(multipliers)


class MultiplierListView(ListAPIView):
    queryset = Multiplier.objects.all()
    serializer_class = MultiplierReadSerializer
    permission_classes = [IsStaffPermission]
    pagination_class = StandardPageNumberPagination
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]
    search_fields = ["name"]
    filterset_fields = ["app"]
    ordering_fields = ["-created_at"]
