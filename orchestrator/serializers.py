from rest_framework import serializers

from commons.constants import BettingApp


class SeedSelectorSerializer(serializers.Serializer):
    app = serializers.ChoiceField(
        choices=BettingApp.list(),
        required=True,
        error_messages={
            "required": "The 'app' query parameter is required.",
            "invalid_choice": "The 'app' name is not valid",
        },
    )
