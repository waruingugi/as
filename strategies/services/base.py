from abc import ABC, abstractmethod
from collections import deque

from strategies.constants import (
    DEFAULT_BANK_ROLL,
    DEFAULT_CRASH_TARGET,
    DEFAULT_STAKE,
    LedgerEntry,
)


class Strategy(ABC):
    def __init__(self, family: str) -> None:
        self.family = family

        self._has_started = False
        self._is_paused = True
        self._is_exited = True

        self._crash_target = DEFAULT_CRASH_TARGET
        self.bank_roll = DEFAULT_BANK_ROLL
        self._current_balance = DEFAULT_BANK_ROLL
        self._stake = DEFAULT_STAKE

        self._ledger: deque[LedgerEntry] = deque()

        self.no_of_losses = 0
        self.no_of_wins = 0
        self.multipliers = []

    def reset(self) -> None:
        """
        Resets the state of the strategy to its default values.
        This method initializes or resets the following attributes:
        - `_has_started`: Indicates whether the strategy has started.
        - `_crash_target`: The target value for a crash, set to the default.
        - `_ledger`: A deque to store ledger entries, initialized as empty.
        - `_stake`: The default stake value.
        - `no_of_losses`: The number of losses, initialized to 0.
        - `no_of_wins`: The number of wins, initialized to 0.
        - `multipliers`: A list to store multipliers, initialized as empty.
        - `bank_roll`: The default bank roll value.
        - `_current_balance`: The current balance, set to the default bank roll value.
        - `_is_paused`: Indicates whether the strategy is paused, set to True.
        - `_is_exited`: Indicates whether the strategy has exited, set to True.
        """

        self._ledger: deque[LedgerEntry] = deque()
        self._stake = DEFAULT_STAKE

        self.has_started = False
        self.is_paused = True
        self.has_exited = True

        self.bank_roll = DEFAULT_BANK_ROLL
        self.current_balance = DEFAULT_BANK_ROLL
        self.crash_target = DEFAULT_CRASH_TARGET

        self.no_of_losses = 0
        self.no_of_wins = 0
        self.multipliers = []

    def __call__(self, *args, **kwargs):
        return self.reset()

    @abstractmethod
    def execute(self, *args, **kwargs):
        """
        Execute the strategy with the given arguments.
        This method should be overridden by subclasses to implement the specific
        strategy logic.
        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        Returns:
            None
        """

        pass

    @abstractmethod
    def _should_bet(self) -> bool:
        """
        Determines whether a bet should be placed based on the implemented strategy.
        Returns:
            bool: True if a bet should be placed, False otherwise.
        """

        pass

    def _on_win(self):
        """
        This method should be overridden in subclasses to define the behavior
        when a win condition is met. It is intended to be called when a win
        event occurs.
        Raises:
            NotImplementedError: If the method is not overridden in a subclass.
        """

        raise NotImplementedError

    def _on_loss(self):
        """
        This method should be overridden in subclasses to define the behavior
        when a loss occurs. It is intended to be called when a loss condition
        is met.
        Raises:
            NotImplementedError: If the method is not overridden in a subclass.
        """

        raise NotImplementedError

    @property
    def bet_history(self) -> list:
        return list(self._ledger)

    @property
    def no_of_bets(self) -> int:
        return len(self._ledger)

    @property
    def has_exited(self) -> bool:
        """
        Check if the exit condition has been met.
        Returns:
            bool: True if the exit condition has been met, False otherwise.
        """

        return self._is_exited

    @has_exited.setter
    def has_exited(self, value: bool) -> None:
        """
        Sets the exit status of the strategy.
        Args:
            value (bool): The exit status to set. True if the strategy has exited, False otherwise.
        """

        self._is_exited = value

    @property
    def has_started(self) -> bool:
        """
        Check if the strategy has started.
        Returns:
            bool: True if the strategy has started, False otherwise.
        """

        return self._has_started

    @has_started.setter
    def has_started(self, value: bool) -> None:
        """
        Sets the '_has_started' attribute to the given boolean value.
        Args:
            value (bool): The boolean value to set for '_has_started'.
        """

        self._has_started = value

    @property
    def current_balance(self) -> float:
        """
        Retrieve the current balance.
        Returns:
            float: The current balance.
        """

        return self._current_balance

    @current_balance.setter
    def current_balance(self, value: float) -> None:
        """
        Sets the current balance to the specified value.
        Args:
            value (float): The new balance to be set.
        """

        self._current_balance = value

    @property
    def stake(self) -> float:
        """
        Returns the stake value.
        Returns:
            float: The stake value.
        """

        return self._stake

    @stake.setter
    def stake(self, value: float) -> None:
        self._stake = value

    @property
    def is_paused(self) -> bool:
        """
        Check if the strategy is currently paused.
        Returns:
            bool: True if the strategy is paused, False otherwise.
        """

        return self._is_paused

    @is_paused.setter
    def is_paused(self, value: bool) -> None:
        self._is_paused = value

    @property
    def crash_target(self) -> float:
        """
        Returns the crash target value.
        This method retrieves the crash target value, which is a float representing
        the target value for a crash event that is required to make a profit.
        Returns:
            float: The crash target value.
        """

        return self._crash_target

    @crash_target.setter
    def crash_target(self, value: float) -> None:
        self._crash_target = value

    @property
    def is_profitable(self) -> bool:
        """
        Determines if the current balance is greater than the initial bank roll.
        Returns:
            bool: True if the current balance is greater than the bank roll, False otherwise.
        """

        return self.current_balance > self.bank_roll

    @property
    def return_on_investment(self) -> float:
        """
        Calculate the current Return on Investment (ROI).
        Returns:
            float: The current ROI as a percentage.
        """
        if self.bank_roll == 0:
            return 0.0
        return ((self.current_balance - self.bank_roll) / self.bank_roll) * 100

    def _record_bet(
        self,
        *,
        stake: float,
        cash_out_at: float,
        flew_away_at: float,
        initial_balance: float,
        final_balance: float,
    ) -> None:
        """
        Records a bet in the ledger with the given parameters.
        Args:
            stake (float): The amount of money placed on the bet.
            cash_out_at (float): The value at which the bet was cashed out.
            flew_away_at (float): The value at which the aviator plane crashed.
            initial_balance (float): The initial balance before placing the bet.
            final_balance (float): The final balance after the bet is resolved.
        Returns:
            None
        """
        entry = LedgerEntry(
            stake=stake,
            cash_out_at=cash_out_at,
            flew_away_at=flew_away_at,
            initial_balance=initial_balance,
            final_balance=final_balance,
            net_profit=abs(final_balance - initial_balance),
            is_profitable=final_balance > initial_balance,
        )
        self._ledger.append(entry)

    def _next_bet(self) -> dict:
        """Returns a suggestion of the next bet to be placed."""
        return {
            "stake": self.stake,
            "cash_out_at": self.crash_target,
            "flew_away_at": None,
            "initial_balance": self.current_balance,
            "final_balance": None,
            "net_profit": None,
            "is_profitable": None,
        }
