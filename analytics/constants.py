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
    "EXTREME": [
        "Odds are huge—risk is equally massive! Bet carefully.",
        "Extremely high chance, but watch for big losses too.",
        "Sky-high odds! Exercise caution to avoid major losses.",
        "Huge crash chance! Over 20x might come soon, stay wary.",
        "Extreme potential—bet wisely or risk a painful downfall.",
    ],
    "HIGH": [
        "High 20x odds—great opportunity, but bet responsibly.",
        "Strong chance of 20x soon—act now but tread carefully.",
        "High probability of big gains—still, manage your risk.",
        "Chance is solid! A 20x crash may be near—bet prudently.",
        "Big payout likely—just don’t overextend your bankroll.",
    ],
    "MODERATE": [
        "Moderate shot at 20x. Weigh options before betting.",
        "Fair odds—20x might happen, but caution is advised.",
        "Chance at 20x is decent—bet carefully to minimize risk.",
        "Moderate 20x potential—mind your stakes and time it well.",
        "20x could occur—consider a measured wager approach.",
    ],
    "LOW": [
        "Low odds for 20x—waiting might be the wiser choice.",
        "Chance is slim. Over 20x seems unlikely right now.",
        "Minimal 20x potential—save funds for a better moment.",
        "Probably not worth the bet—20x crash is improbable.",
        "Small chance for 20x—holding off could be smarter.",
    ],
}
