from rest_framework import serializers

from commons.errors import ErrorCodes
from observers.models import Multiplier

# from observers.utils import parse_multipliers


class MultiplierCreateSerializer(serializers.Serializer):
    multipliers = serializers.ListField(
        child=serializers.FloatField(),
        allow_empty=False,
        error_messages={
            "not_a_list": ErrorCodes.INVALID_MULTIPLIER_STRING.value,
            "empty": ErrorCodes.MULTIPLIERS_NOT_FOUND.value,
        },
    )
    room_no = serializers.IntegerField(required=False)


class MultiplierReadSerializer(serializers.ModelSerializer):
    app = serializers.CharField(source="worker.app")
    name = serializers.CharField(source="worker.name")

    class Meta:
        model = Multiplier
        fields = ["crash", "app", "name"]


class CrashSerializer(serializers.Serializer):
    created_at = serializers.DateTimeField()
    crash = serializers.DecimalField(max_digits=10, decimal_places=2)


class WorkerHistorySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    crash = serializers.ListField(child=CrashSerializer())
