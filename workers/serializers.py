from uuid import uuid4

from rest_framework import serializers

from workers.models import Worker


class WorkerBaseSerializer(serializers.ModelSerializer):
    key = serializers.UUIDField(default=uuid4, required=False)

    class Meta:
        model = Worker
        fields = "__all__"


class WorkerCreateSerializer(WorkerBaseSerializer):
    class Meta(WorkerBaseSerializer.Meta):
        read_only_fields = ("id", "created_at", "updated_at")


class WorkerListSerializer(WorkerBaseSerializer):
    pass


class WorkerUpdateSerializer(WorkerBaseSerializer):
    class Meta(WorkerBaseSerializer.Meta):
        read_only_fields = ("id", "created_at", "updated_at")
