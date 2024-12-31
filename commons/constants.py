from enum import Enum

# LENGTH OF WORKER API KEYS
WORKER_API_KEY_LEN: int = 32


class BettingApps(str, Enum):
    BETIKA = "BETIKA"
