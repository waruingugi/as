from enum import Enum


class CrashesToMonitor(float, Enum):
    """Crashes used to calculate probabilities."""

    OVER_20X = 20.0
    # OVER_50X = 50.0

    @staticmethod
    def list():
        return [crash.value for crash in CrashesToMonitor]


# Default Cache duration for Probability Analytics class
PROB_DEFAULT_CACHE_DURATION: int = 600

# Over 20x suggestions
OVER_20X_SUGGESTIONS = {
    "HIGH": [
        "High crash chance! Bet soon for over 20x profit.",
        "Strong odds! Over 20x is likely—place your bet now.",
        "Great chance ahead! Aim for that 20x boost.",
        "Big potential gain! Jump in for over 20x returns.",
        "Don't miss out! 20x crash probability is high.",
    ],
    "MODERATE": [
        "Moderate chance for 20x. Weigh options before betting.",
        "Slight risk. 20x might happen, but caution is advised.",
        "Moderate odds of big win. Bet carefully for 20x.",
        "Chance is fair, but weigh your bets for a 20x payout.",
        "20x is possible, but keep an eye on your bankroll.",
    ],
    "LOW": [
        "Low chance of hitting 20x. Safer to wait for better odds.",
        "Chances are slim. Over 20x seems unlikely right now.",
        "Odds for 20x are low. It's probably best to hold off.",
        "20x looks unlikely. You might save funds for later bets.",
        "Low probability now. Holding your bet could be wiser.",
    ],
}
