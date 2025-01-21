from rest_framework import serializers

from commons.constants import SeedNames
from commons.utils import generate_uuid
from workers.models import Worker


class WorkerBaseSerializer(serializers.ModelSerializer):
    key = serializers.CharField(default=generate_uuid, required=False)

    class Meta:
        model = Worker
        fields = "__all__"


class WorkerCreateSerializer(WorkerBaseSerializer):
    name = serializers.ChoiceField(choices=SeedNames.list(), required=True)

    class Meta(WorkerBaseSerializer.Meta):
        read_only_fields = ("id", "created_at", "updated_at")


class WorkerListSerializer(WorkerBaseSerializer):
    pass


class WorkerUpdateSerializer(WorkerBaseSerializer):
    class Meta(WorkerBaseSerializer.Meta):
        read_only_fields = ("id", "created_at", "updated_at")


class WorkerReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ("app", "name")
