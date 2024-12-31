from enum import Enum
from typing import List

# LENGTH OF WORKER API KEYS
WORKER_API_KEY_LEN = 32


class BettingApps(Enum):
    BETIKA = "BETIKA"

    @classmethod
    def list_(cls) -> List:
        apps = {app.value for app in cls}
        return list(apps)
