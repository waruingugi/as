from dataclasses import dataclass
from enum import Enum


# RECORD BETS LIKE A LEDGER
@dataclass
class LedgerEntry:
    stake: float
    cash_out_at: float
    flew_away_at: float
    net_profit: float
    is_profitable: bool
    initial_balance: float
    final_balance: float


# DEFAULT BANK ROLL FOR STRATEGIES
DEFAULT_BANK_ROLL: float = float(1000)

# DEFAULT CRASH TARGET
DEFAULT_CRASH_TARGET: float = 1.00

# DEFAULT STAKE
DEFAULT_STAKE: float = 50.00

# DEFAULT CRASH START TRIGGER
DEFAULT_CRASH_START_TRIGGER: float = 20.00


# BETTING STRATEGY FAMILIES
class BettingStrategyFamily(str, Enum):
    MARTINGALE = "Martingale"
