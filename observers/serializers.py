from rest_framework import serializers

from commons.errors import ErrorCodes
from observers.models import Multiplier
from observers.utils import parse_multipliers


class MultiplierCreateSerializer(serializers.Serializer):
    multipliers = serializers.CharField()

    def validate_multipliers(self, value) -> list[float] | None:
        """
        Custom validation for the multipliers field to ensure it's properly formatted.
        """
        try:
            # Replace clean_payouts with actual parsing logic
            payouts = parse_multipliers(value)
            if not payouts:
                raise serializers.ValidationError(
                    ErrorCodes.MULTIPLIERS_NOT_FOUND.value
                )
            return payouts
        except ValueError:
            raise serializers.ValidationError(
                ErrorCodes.INVALID_MULTIPLIER_STRING.value
            )


class MultiplierReadSerializer(serializers.ModelSerializer):
    app = serializers.CharField(source="worker.app")
    name = serializers.CharField(source="worker.name")

    class Meta:
        model = Multiplier
        fields = ["crash", "app", "name"]
