import random
from decimal import Decimal

from django.core.cache import cache

from analytics.constants import OVER_20X_SUGGESTIONS, CrashesToMonitor
from analytics.services import Probability
from commons.constants import CacheKeys
from commons.utils import get_room_name, get_worker_health
from observers.services import SignalEvaluator


def format_worker_probabilities(worker) -> dict:
    probabilities = {}

    for crash in CrashesToMonitor.list():
        probability = Probability.calculate_probability(worker.id, crash)
        suggestion = ""
        # Add suggestions only for over_20x
        if crash == CrashesToMonitor.OVER_20X.value:
            suggestion = get_over_20x_suggestion(worker.id, probability)

        probabilities[f"over_{int(crash)}x"] = {
            "probability": probability,
            "suggestion": suggestion,  # Suggestion logic to be implemented later
        }

    return {
        "id": worker.id,
        "name": worker.name,
        "room_name": get_room_name(worker.app, worker.name),
        "is_healthy": get_worker_health(str(worker.id)),
        "probability": probabilities,
    }


# TODO: Calculate probabilities from DB and derive suggestions.
# This will be more dynamic and complex in future
def get_over_20x_suggestion(worker_id: str, probability: float) -> str:
    """This function generates a suggestion based on the probability of a payout.
    We cache the suggestion to prevent users from getting different suggestions for the same probability range.
    """
    signal_evaluator = SignalEvaluator()
    triggered_recently = signal_evaluator.has_been_triggered_recently(worker_id)

    # Adjust the current range based on recent signal trigger
    if probability >= Decimal(70) and triggered_recently:
        current_range = "HIGH"
    elif probability >= Decimal(75) and not triggered_recently:
        current_range = "MODERATE"
    else:
        current_range = "LOW"

    cache_key = CacheKeys.WORKER_PROBABILITY_SUGGESTION.format(worker_id, current_range)
    cached_suggestion = cache.get(cache_key)

    if cached_suggestion and cached_suggestion["range"] == current_range:
        return cached_suggestion["suggestion"]

    # Otherwise, generate a new suggestion
    new_suggestion = random.choice(OVER_20X_SUGGESTIONS[current_range])

    # Cache the new suggestion with the current range
    cache.set(
        cache_key,
        {"range": current_range, "suggestion": new_suggestion},
        timeout=60 * 60,
    )

    return new_suggestion


# def get_over_20x_suggestion(worker_id: str, probability: float) -> str:
#     """This function generates a suggestion based on the probability of a payout.
#     We cache the suggestion to prevent users from getting different suggestions for the same probability range.
#     """
#     # Determine the current range
#     if probability >= Decimal(75):
#         current_range = "EXTREME"  # Extreme probability
#     elif probability > Decimal(50):
#         current_range = "HIGH"  # High probability
#     elif probability > Decimal(25):
#         current_range = "MODERATE"  # Moderate probability
#     else:
#         current_range = "LOW"  # Low probability
#
#     cache_key = CacheKeys.WORKER_PROBABILITY_SUGGESTION.format(worker_id, current_range)
#     cached_suggestion = cache.get(cache_key)
#
#     if cached_suggestion and cached_suggestion["range"] == current_range:
#         return cached_suggestion["suggestion"]
#
#     # Otherwise, generate a new suggestion
#     new_suggestion = random.choice(OVER_20X_SUGGESTIONS[current_range])
#
#     # Cache the new suggestion with the current range
#     cache.set(
#         cache_key, {"range": current_range, "suggestion": new_suggestion}, timeout=None
#     )
#
#     return new_suggestion
