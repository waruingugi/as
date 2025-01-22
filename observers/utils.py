from collections import defaultdict

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


def calculate_jaccard_similarity(set_1, set_2) -> float:
    """
    Calculate Jaccard similarity between two sets.
    """
    intersection = len(set_1 & set_2)
    union = len(set_1 | set_2)
    return intersection / union if union > 0 else 0


def find_similar_workers(worker_payouts, threshold=0.8) -> dict:
    """
    Compare workers for similarity based on Jaccard similarity.

    Args:
        worker_payouts (dict): Dictionary of worker IDs and their payout sets.
        threshold (float): Similarity threshold to consider workers as "similar".

    Returns:
        dict: Matched worker pairs and their similarity scores.
    """
    matched_workers = defaultdict(list)
    worker_ids = list(worker_payouts.keys())

    for i in range(len(worker_ids)):
        for j in range(i + 1, len(worker_ids)):
            worker_1 = worker_ids[i]
            worker_2 = worker_ids[j]

            # Calculate similarity
            similarity = calculate_jaccard_similarity(
                worker_payouts[worker_1], worker_payouts[worker_2]
            )
            if similarity >= threshold:
                matched_workers[(worker_1, worker_2)] = similarity

    return matched_workers
