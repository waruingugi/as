from commons.logger import logger
from strategies.constants import DEFAULT_CRASH_START_TRIGGER
from strategies.services import medium_step_ladder, short_step_ladder, tall_step_ladder


class StrategyManager:
    def __init__(self):
        """Initialize all strategy instances."""
        self.strategies = [short_step_ladder, medium_step_ladder, tall_step_ladder]

    def execute_all(self, crash_value):
        """Executes all strategies with the new crash multiplier."""
        logger.info("Executing strategies...")
        for strategy in self.strategies:
            strategy.execute([crash_value])

        # Reset all strategies if crash is 20.00 or higher
        if crash_value >= DEFAULT_CRASH_START_TRIGGER:
            logger.info("Resetting all strategies...")
            self.reset_all()

    def reset_all(self):
        """Resets all strategies to their initial state."""
        for strategy in self.strategies:
            strategy.reset()


# Singleton instance of the manager
strategy_manager = StrategyManager()
