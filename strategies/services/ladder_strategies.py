from strategies.constants import DEFAULT_STOP_LOSS, BettingStrategyFamily
from strategies.services import Strategy


class LadderBaseStrategy(Strategy):
    def __init__(self) -> None:
        super().__init__(family=BettingStrategyFamily.MARTINGALE.value)
        self.default_crash_target = 2.00
        self._crash_target = 2.00
        self.stop_loss = DEFAULT_STOP_LOSS

        self.start_triggers = {"multipliers_are_below": 2.00, "multipliers_len": 3}

    def reset(self) -> None:
        super().reset()

    def execute(self, multipliers: list) -> None:
        for crash in multipliers:
            self.multipliers.append(crash)

            if self._should_bet():
                initial_balance = self.current_balance
                stake = self.stake
                cash_out_at = self.crash_target

                self.current_balance -= self.stake
                if crash >= self.crash_target:
                    self._on_win()
                else:
                    self._on_loss()

                self._record_bet(
                    stake=stake,
                    cash_out_at=cash_out_at,
                    initial_balance=initial_balance,
                    final_balance=self.current_balance,
                    flew_away_at=crash,
                )

    def _should_bet(self) -> bool:
        if self.has_started:  # If strategy is already running (i.e placing bets)
            return not self.has_exited

        else:  # Check if start trigger conditions are met
            if (
                self.current_balance > self.stake
                and len(self.multipliers) > self.start_triggers["multipliers_len"]
                and all(
                    multiplier < self.start_triggers["multipliers_are_below"]
                    for multiplier in self.multipliers[
                        -self.start_triggers["multipliers_len"] - 1 : -1
                    ]
                )
            ):
                self.has_started = True
                self.has_exited = False
                return True

        return False

    def _on_win(self) -> None:
        self.current_balance += self.stake * self.crash_target
        self.no_of_wins += 1

        self.crash_target = self.default_crash_target
        self.has_exited = True

    def _on_loss(self):
        self.no_of_losses += 1
        self.crash_target += 1.00

        if (self.no_of_losses >= self.stop_loss) or (self.current_balance <= 0):
            self.has_exited = True


class TallStepLadderStrategy(LadderBaseStrategy):
    """
    STEP 1: Wait for 7 crashes that are under 2.00x to occur
    STEP 2: On the 8th crash, start betting with the first target crash being 2.00x
        STEP 2.1: If the crash is over or equal crash_target, cashout at the crash_target.
        STEP 2.2: If the crash is under 2.00x, increase the target crash by 1. Which means the next crash_target is 3.00x
    STEP 3: Repeat STEP 2 until you reach you the reach stop loss or hit a win.
    """

    DEFAULT_CRASH_TARGET = 2.00
    START_TRIGGERS = {"multipliers_are_below": 2.00, "multipliers_len": 7}

    def __init__(self) -> None:
        super().__init__()
        self.default_crash_target = self.DEFAULT_CRASH_TARGET
        self._crash_target = self.DEFAULT_CRASH_TARGET
        self.stop_loss = DEFAULT_STOP_LOSS
        self.start_triggers = (
            self.START_TRIGGERS.copy()
        )  # Use `.copy()` to avoid modifying class-level dict

    def reset(self) -> None:
        """Reset the strategy to its initial values."""
        super().reset()
        self.default_crash_target = self.DEFAULT_CRASH_TARGET
        self._crash_target = self.DEFAULT_CRASH_TARGET
        self.stop_loss = DEFAULT_STOP_LOSS
        self.start_triggers = self.START_TRIGGERS.copy()


class MediumStepLadderStrategy(LadderBaseStrategy):
    """
    STEP 1: Wait for 5 crashes that are under 2.00x to occur
    STEP 2: On the 6th crash, start betting with the first target crash being 2.00x
        STEP 2.1: If the crash is over or equal crash_target, cashout at the crash_target.
        STEP 2.2: If the crash is under 2.00x, increase the target crash by 1. Which means the next crash_target is 3.00x
    STEP 3: Repeat STEP 2 until you reach you the reach stop loss or hit a win.
    """

    DEFAULT_CRASH_TARGET = 2.00
    START_TRIGGERS = {"multipliers_are_below": 2.00, "multipliers_len": 5}

    def __init__(self) -> None:
        super().__init__()
        self.default_crash_target = self.DEFAULT_CRASH_TARGET
        self._crash_target = self.DEFAULT_CRASH_TARGET
        self.stop_loss = DEFAULT_STOP_LOSS
        self.start_triggers = (
            self.START_TRIGGERS.copy()
        )  # Use `.copy()` to avoid modifying class-level dict

    def reset(self) -> None:
        """Reset the strategy to its initial values."""
        super().reset()
        self.default_crash_target = self.DEFAULT_CRASH_TARGET
        self._crash_target = self.DEFAULT_CRASH_TARGET
        self.stop_loss = DEFAULT_STOP_LOSS
        self.start_triggers = self.START_TRIGGERS.copy()


class ShortStepLadderStrategy(LadderBaseStrategy):
    """
    STEP 1: Wait for 3 crashes that are under 2.00x to occur
    STEP 2: On the 4th crash, start betting with the first target crash being 2.00x
        STEP 2.1: If the crash is over or equal crash_target, cashout at the crash_target.
        STEP 2.2: If the crash is under 2.00x, increase the target crash by 1. Which means the next crash_target is 3.00x
    STEP 3: Repeat STEP 2 until you reach you the reach stop loss or hit a win.
    """

    DEFAULT_CRASH_TARGET = 2.00
    START_TRIGGERS = {"multipliers_are_below": 2.00, "multipliers_len": 3}

    def __init__(self) -> None:
        super().__init__()
        self.default_crash_target = self.DEFAULT_CRASH_TARGET
        self._crash_target = self.DEFAULT_CRASH_TARGET
        self.stop_loss = DEFAULT_STOP_LOSS
        self.start_triggers = (
            self.START_TRIGGERS.copy()
        )  # Use `.copy()` to avoid modifying class-level dict

    def reset(self) -> None:
        """Reset the strategy to its initial values."""
        super().reset()
        self.default_crash_target = self.DEFAULT_CRASH_TARGET
        self._crash_target = self.DEFAULT_CRASH_TARGET
        self.stop_loss = DEFAULT_STOP_LOSS
        self.start_triggers = self.START_TRIGGERS.copy()


tall_step_ladder = TallStepLadderStrategy()
medium_step_ladder = MediumStepLadderStrategy()
short_step_ladder = ShortStepLadderStrategy()
