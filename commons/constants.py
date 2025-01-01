from enum import Enum

from django.contrib.auth import get_user_model

# Model Constants
User = get_user_model()

# LENGTH OF WORKER API KEYS
WORKER_API_KEY_LEN: int = 32


class BettingApps(str, Enum):
    BETIKA = "BETIKA"
