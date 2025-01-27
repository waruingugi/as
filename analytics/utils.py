from analytics.constants import CrashesToMonitor
from analytics.services import Probability


def format_worker_probabilities(worker) -> dict:
    probabilities = {}

    for crash in CrashesToMonitor:
        value = crash.value
        probability = Probability.calculate_probability(worker.id, value)
        probabilities[f"over_{int(value)}x"] = {
            "probability": probability,
            "suggestion": "",  # Suggestion logic to be implemented later
        }

    return {
        "id": worker.id,
        "name": worker.name,
        "probability": probabilities,
    }
