from rest_framework import serializers

from commons.constants import BettingApps


class SeedSelectorSerializer(serializers.Serializer):
    app = serializers.ChoiceField(
        choices=[(app.value, app.value) for app in BettingApps],
        required=True,
        error_messages={
            "required": "The 'app' query parameter is required.",
            "invalid_choice": "The 'app' name is not valid",
        },
    )
