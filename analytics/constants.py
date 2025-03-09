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

# # Over 20x suggestions
# OVER_20X_SUGGESTIONS = {
#     "EXTREME": [
#         "Odds are high and risk is equally high! Bet carefully.",
#         "Extremely high chance, but watch for big losses too.",
#         "Sky-high odds! Exercise caution to avoid major losses.",
#         "Huge crash chance! Over 20x might come soon, stay wary.",
#         "Extreme potential. Bet wisely or risk a painful downfall.",
#     ],
#     "HIGH": [
#         "High 20x odds. Great opportunity, but bet responsibly.",
#         "Strong chance of 20x soon, act now but tread carefully.",
#         "High probability of big gains—still, manage your risk.",
#         "Chance is solid! A 20x crash may be near—bet prudently.",
#         "Big payout likely—just don’t overextend your bankroll.",
#     ],
#     "MODERATE": [
#         "Moderate shot at 20x. Weigh options before betting.",
#         "Fair odds—20x might happen, but caution is advised.",
#         "Chance at 20x is decent—bet carefully to minimize risk.",
#         "Moderate 20x potential—mind your stakes and time it well.",
#         "20x could occur—consider a measured wager approach.",
#     ],
#     "LOW": [
#         "Low odds for 20x—waiting might be the wiser choice.",
#         "Chance is slim. Over 20x seems unlikely right now.",
#         "Minimal 20x potential—save funds for a better moment.",
#         "Probably not worth the bet—20x crash is improbable.",
#         "Small chance for 20x—holding off could be smarter.",
#     ],
# }
OVER_20X_SUGGESTIONS = {
    "EXTREME": [
        "Odds are high! Bet now but don’t go all in.",
        "Very high chance for 20x. But it's risky.",
        "Sky high odds! This may be big win or loss.",
        "Extreme chances. Your call on how to play this.",
        "An over 20x may appear any moment from now.",
    ],
    "HIGH": [
        "High 20x odds. This could be your moment.",
        "Strong chance for an over 20x. Now is the time.",
        "An over 20x is likely to happen in a few minutes.",
        "20x is around the corner. Start betting now.",
        "Chance is solid. Take the shot if you’re ready.",
    ],
    "MODERATE": [
        "Moderate 20x shot. Bet if you feel confident.",
        "Fair chance for 20x. Make your move wisely.",
        "20x could happen. Bet small or wait it out.",
        "Decent odds. Your call on how to play this.",
        "Moderate chance. Bet now or hold off, your pick.",
    ],
    "LOW": [
        "Low odds for 20x. Waiting might be smarter.",
        "Chance is slim. Bet on low crashes for now.",
        "Minimal 20x chance. Skip the next few rounds.",
        "Probably not worth it. An over 20x is unlikely.",
        "Small chance for 20x. Wait for better chances.",
    ],
}
