import random
from decimal import Decimal

from analytics.constants import OVER_20X_SUGGESTIONS, CrashesToMonitor
from analytics.services import Probability


def format_worker_probabilities(worker) -> dict:
    probabilities = {}

    for crash in CrashesToMonitor.list():
        probability = Probability.calculate_probability(worker.id, crash)
        suggestion = ""
        # Add suggestions only for over_20x
        if crash == CrashesToMonitor.OVER_20X.value:
            suggestion = get_over_20x_suggestion(probability)

        probabilities[f"over_{int(crash)}x"] = {
            "probability": probability,
            "suggestion": suggestion,  # Suggestion logic to be implemented later
        }

    return {
        "id": worker.id,
        "name": worker.name,
        "probability": probabilities,
    }


# TODO: Calculate probabilities from DB and derive suggestions.
# This will be more dynamic and complex in future
def get_over_20x_suggestion(probability: float) -> str:
    if probability >= Decimal(75):  # Extreme probability
        return random.choice(OVER_20X_SUGGESTIONS["EXTREME"])
    elif probability > Decimal(50):  # High probability
        return random.choice(OVER_20X_SUGGESTIONS["HIGH"])
    elif probability > Decimal(25):  # Moderate probability
        return random.choice(OVER_20X_SUGGESTIONS["MODERATE"])
    else:  # Low probability
        return random.choice(OVER_20X_SUGGESTIONS["LOW"])
