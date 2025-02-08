from django.test import TestCase

from strategies.constants import DEFAULT_BANK_ROLL, DEFAULT_STAKE
from strategies.services import (
    medium_step_ladder,
    short_step_ladder,
    tall_step_ladder,
)


class LadderStrategyTests(TestCase):
    def setUp(self):
        """Set up fresh instances for each test"""
        self.short_ladder = short_step_ladder
        self.medium_ladder = medium_step_ladder
        self.tall_ladder = tall_step_ladder

    def tearDown(self) -> None:
        """Clean up after each test"""
        self.short_ladder.reset()
        self.medium_ladder.reset()
        self.tall_ladder.reset()

    def test_initialization(self) -> None:
        """Test if strategies initialize with the correct values"""
        self.assertEqual(self.short_ladder.current_balance, DEFAULT_BANK_ROLL)
        self.assertEqual(self.short_ladder.stake, DEFAULT_STAKE)
        self.assertEqual(self.short_ladder.crash_target, 2.00)
        self.assertEqual(self.short_ladder.start_triggers["multipliers_len"], 3)

        self.assertEqual(self.medium_ladder.start_triggers["multipliers_len"], 5)
        self.assertEqual(self.tall_ladder.start_triggers["multipliers_len"], 7)

    def test_betting_trigger(self) -> None:
        """Check if betting starts when conditions are met"""
        self.short_ladder.execute([1.5, 1.8, 1.9, 1.5])
        self.assertTrue(self.short_ladder.has_started)
        self.assertFalse(self.short_ladder.has_exited)

        self.medium_ladder.execute([1.3, 1.5, 1.8, 1.9, 1.6, 1.5])
        self.assertTrue(self.medium_ladder.has_started)
        self.assertFalse(self.medium_ladder.has_exited)

        self.tall_ladder.execute([1.1, 1.2, 1.3, 1.4, 1.7, 1.8, 1.9, 1.5])
        self.assertTrue(self.tall_ladder.has_started)
        self.assertFalse(self.tall_ladder.has_exited)

    def test_on_win(self) -> None:
        """Simulate a winning bet"""
        self.short_ladder.execute([1.5, 1.6, 1.8, 2.2])
        self.assertGreater(self.short_ladder.current_balance, DEFAULT_BANK_ROLL)
        self.assertTrue(self.short_ladder.has_exited)

        self.short_ladder.reset()
        for _ in range(self.short_ladder.start_triggers["multipliers_len"]):
            self.short_ladder.execute([1.5])

        self.assertFalse(self.short_ladder.has_started)

        self.short_ladder.execute([40.5])
        self.assertTrue(self.short_ladder.is_profitable)
        self.assertTrue(self.short_ladder.has_exited)

    def test_on_loss(self) -> None:
        """Simulate a loss scenario"""
        self.short_ladder.execute([1.5, 1.6, 1.8, 1.4])
        self.assertEqual(self.short_ladder.no_of_losses, 1)
        self.assertEqual(self.short_ladder.crash_target, 3.00)

    def test_reset(self) -> None:
        """Ensure reset restores default values"""
        self.short_ladder.execute([1.5, 1.6, 1.8, 2.2])
        self.short_ladder.reset()

        self.assertEqual(self.short_ladder.current_balance, DEFAULT_BANK_ROLL)
        self.assertEqual(self.short_ladder.crash_target, 2.00)
        self.assertEqual(self.short_ladder.no_of_losses, 0)
        self.assertEqual(self.short_ladder.no_of_wins, 0)
        self.assertTrue(self.short_ladder.has_exited)
