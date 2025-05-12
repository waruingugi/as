from commons.constants import BettingApp


def generate_default_signal_pref() -> dict:
    """Generate the default signal preference for a user in the SignalSettings model."""
    default_preference = {}
    for app in BettingApp.list():
        default_preference[app] = {
            "subscribed": False,
            "probability": None,
        }
    return default_preference
