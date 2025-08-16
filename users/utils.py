from commons.constants import BettingApp


def default_signal_preference() -> dict:
    """Generate the default signal preference for a user in the SignalSettings model."""
    default_preference = {}
    for app in BettingApp.list():
        default_preference[app] = {
            "subscribed": False,
            # "trigger": None,
        }
    return default_preference
