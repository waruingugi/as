from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.generics import CreateAPIView, ListAPIView

from commons.pagination import (
    StandardPageNumberPagination,
)
from commons.permissions import IsStaffPermission, IsWorkerPermission
from observers.models import Multiplier
from observers.serializers import MultiplierCreateSerializer, MultiplierReadSerializer
from observers.utils import get_new_multipliers


class MultiplierCreateView(CreateAPIView):
    serializer_class = MultiplierCreateSerializer
    permission_classes = [IsWorkerPermission]

    def perform_create(self, serializer):
        multipliers_list = serializer.validated_data["multipliers"]

        # Reverse the multipliers_list because the last element is the earliest payout
        new_multipliers = get_new_multipliers(self.worker.id, multipliers_list)
        new_multipliers.reverse()

        multipliers = [
            Multiplier(worker=self.worker, crash=crash) for crash in new_multipliers
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
    search_fields = ["worker__name", "worker__app"]
    ordering_fields = ["-created_at"]
