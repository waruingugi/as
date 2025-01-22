from observers.models import Multiplier

# def parse_multipliers(input_string: str) -> list[float]:
#     if not input_string or not isinstance(input_string, str):
#         raise ValueError(ErrorCodes.EMPTY_MULTIPLIER_STRING.value)

#     try:
#         # Split the string by commas and strip spaces
#         multiplier_str = [value.strip() for value in input_string.split(",")]

#         # Remove the trailing 'x' and convert to float
#         multipliers = [float(payout.rstrip("x")) for payout in multiplier_str]

#         return multipliers
#     except Exception:
#         raise ValueError(ErrorCodes.INVALID_MULTIPLIER_STRING.value)


def get_new_multipliers(
    worker_id: str, new_multipliers_list: list[float]
) -> list[float]:
    """Perform sequence matching between two lists to find new payouts"""
    sequence_length = len(new_multipliers_list)

    previous_multipliers = (
        Multiplier.objects.filter(worker_id=worker_id)
        .values_list("crash", flat=True)
        .order_by("-created_at")[:sequence_length]
    )
    previous_multiplier_list = [float(payout) for payout in previous_multipliers]

    for i in range(sequence_length):
        if (
            new_multipliers_list[i:]
            == previous_multiplier_list[: (sequence_length - i)]
        ):
            return new_multipliers_list[:i]

    return new_multipliers_list
