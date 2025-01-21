from rest_framework import serializers

from commons.constants import BettingApps


class SeedSelectorSerializer(serializers.Serializer):
    app = serializers.ChoiceField(
        choices=BettingApps.list(),
        required=True,
        error_messages={
            "required": "The 'app' query parameter is required.",
            "invalid_choice": "The 'app' name is not valid",
        },
    )
