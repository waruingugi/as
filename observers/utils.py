from decimal import Decimal

from commons.errors import ErrorCodes


def parse_multipliers(input_string: str) -> list[Decimal]:
    if not input_string or not isinstance(input_string, str):
        raise ValueError(ErrorCodes.EMPTY_MULTIPLIER_STRING.value)

    try:
        # Split the string by commas and strip spaces
        multiplier_str = [value.strip() for value in input_string.split(",")]

        # Remove the trailing 'x' and convert to Decimal
        multipliers = [Decimal(payout.rstrip("x")) for payout in multiplier_str]

        return multipliers
    except Exception:
        raise ValueError(ErrorCodes.INVALID_MULTIPLIER_STRING.value)
