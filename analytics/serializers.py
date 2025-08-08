from rest_framework import serializers


# Serializer for the probability response
class ProbabilitySerializer(serializers.Serializer):
    probability = serializers.DecimalField(decimal_places=2, max_digits=5)
    suggestion = serializers.CharField()


class WorkerProbabilitySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_healthy = serializers.BooleanField(required=False)
    probability = serializers.DictField(child=ProbabilitySerializer())
