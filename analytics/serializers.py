from rest_framework import serializers


# Serializer for the probability response
class ProbabilitySerializer(serializers.Serializer):
    probability = serializers.FloatField()
    suggestion = serializers.CharField()


class WorkerProbabilitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    probability = serializers.DictField(child=ProbabilitySerializer())
