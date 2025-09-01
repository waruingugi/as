from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import Any, Dict, Optional, TypedDict

from django.core.cache import cache

from analytics.constants import CrashesToMonitor
from analytics.services import Probability
from commons.constants import AppPageURL, CacheKeys, NotificationCollapseID
from commons.logger import logger
from commons.utils import get_room_name, get_worker_health, send_push_notification
from notifications.constants import NotificationChannel
from observers.models import Multiplier
from observers.utils import get_app_subscribers

# -----------------------------
# Betting Strategy
# -----------------------------


@dataclass
class BetMetaData:
    strategy_name: str
    initial_bankroll: float
    bankroll: float
    current_round: int
    current_payout: float
    cashout_at: float
    stake: int
    max_rounds: int
    profit: float
    loss: float


class SignalRecordDict(TypedDict, total=False):
    app_name: str
    worker_id: str
    seed_name: str
    room_name: str
    triggered_by_payout_id: Optional[str]
    triggered_by_payout: float
    triggered_at: Optional[str]
    stopped_on_payout_id: Optional[str]
    stopped_on_payout: float
    stopped_at: Optional[str]
    triggered_recently: bool
    is_betting: bool
    metadata: Dict[str, Any]


class AutoBetStrategy:
    name: str = "Autobet"
    stake: int = 20
    cashout_at: float = 20.0
    max_rounds: int = 15

    def start(self, bankroll: Optional[float] = None) -> BetMetaData:
        """Initialize betting strategy metadata and start betting."""
        bankroll = bankroll or (self.stake * self.max_rounds)  # NOTE: 0.0 will be false

        if bankroll < (self.stake * self.max_rounds):  # A simple sanity check
            logger.error(f"Not enough bankroll to start {self.name} strategy")
            raise ValueError("Insufficient bankroll")

        bankroll -= self.stake
        return BetMetaData(
            strategy_name=self.name,
            bankroll=bankroll,
            initial_bankroll=bankroll + self.stake,
            current_round=1,
            current_payout=0.0,  # Will be updated on first bet
            stake=self.stake,
            cashout_at=self.cashout_at,
            max_rounds=self.max_rounds,
            profit=0.0,
            loss=float(self.stake),
        )

    @staticmethod
    def place_bet(meta: BetMetaData) -> BetMetaData:
        """Place a bet and update metadata."""
        meta.bankroll -= meta.stake
        meta.current_round += 1
        meta.loss += meta.stake
        return meta

    @staticmethod
    def stop(payout: float, meta: BetMetaData) -> BetMetaData:
        """Stop betting and update metadata."""
        if payout >= meta.cashout_at:
            net_profit = meta.stake * (meta.cashout_at - 1)
            meta.bankroll += net_profit

            meta.profit += net_profit
            logger.info(f"Bet won at {payout}x. New meta is {asdict(meta)}")
        return meta

    @staticmethod
    def should_stop(meta: BetMetaData, payout: float) -> bool:
        """Should we stop betting?"""
        has_reached_max_rounds = meta.current_round >= meta.max_rounds
        has_insufficient_bankroll = meta.bankroll < meta.stake
        has_won = payout >= meta.cashout_at

        return has_reached_max_rounds or has_insufficient_bankroll or has_won


# -----------------------------
# Signal Evaluation
# -----------------------------


class SignalEvaluator:
    payout_threshold = 20.0
    probability_threshold = 80.0
    max_high_payouts = 6

    def should_send_signal(self, instance: Multiplier) -> bool:
        """All conditions below must be met to send a signal."""
        worker_is_healthy = get_worker_health(str(instance.worker.id))
        return (
            (self._has_low_streak(instance) or self._low_streak_is_close(instance))
            and self._probability_high(instance)
            and not self.has_been_triggered_recently(str(instance.worker.id))
            and worker_is_healthy
        )

    @staticmethod
    def has_been_triggered_recently(worker_id: str) -> bool:
        """Check if a signal has been triggered recently for the worker."""
        cache_key = CacheKeys.SIGNAL_RECORD.format(worker_id)
        data = cache.get(cache_key) or {}
        return bool(data.get("triggered_recently", False))

    def _has_low_streak(self, instance: Multiplier) -> bool:
        """True if within the last 60 minutes, there are 6 or fewer payouts >= threshold"""
        one_hour_ago = instance.created_at - timedelta(hours=1)
        count = Multiplier.objects.filter(
            worker=instance.worker,
            created_at__gte=one_hour_ago,
            created_at__lte=instance.created_at,
            crash__gte=self.payout_threshold,
        ).count()
        return count <= self.max_high_payouts

    def _low_streak_is_close(self, instance: Multiplier) -> bool:
        """
        True if within the last 60 minutes, there are 7(just a magic number) or fewer payouts >= threshold and
        the time difference between the 6th and 7th last payouts is <= 7 minutes.
        """
        close_streak_minutes = 7
        one_hour_ago = instance.created_at - timedelta(hours=1)
        qs = (
            Multiplier.objects.filter(
                worker=instance.worker,
                created_at__gte=one_hour_ago,
                created_at__lte=instance.created_at,
                crash__gte=self.payout_threshold,
            )
            .order_by("-created_at")
            .values_list("created_at", flat=True)
        )

        payout_count = qs.count()
        if payout_count > 7:  # We need at most 7 payouts to consider this condition
            return False

        times = list(qs[5:7])  # Get the 6th and 7th last payouts (if they exist)
        if len(times) < 2:
            return False

        return (times[0] - times[1]) <= timedelta(minutes=close_streak_minutes)

    @staticmethod
    def _get_probability(instance: Multiplier) -> float:
        """Get the current probability of an over 20x payout for the current worker."""
        return Probability.calculate_probability(
            worker_id=str(instance.worker.id),
            crash=CrashesToMonitor.OVER_20X.value,
        )

    def _probability_high(self, instance: Multiplier) -> bool:
        """Check if the probability of an over 20x payout is >= threshold."""
        prob = self._get_probability(instance)
        return prob >= self.probability_threshold

    def should_reset_trigger(self, instance: Multiplier) -> bool:
        """Check if we should reset the triggered_recently flag to False"""
        probability = self._get_probability(instance)
        return probability < self.probability_threshold

    @staticmethod
    def count_payouts_since_trigger(instance: Multiplier, trigger_id: str) -> int:
        """Count how many payouts have occurred since the signal was triggered."""
        trigger_payout = Multiplier.objects.get(id=trigger_id)
        return Multiplier.objects.filter(
            worker=instance.worker,
            created_at__gt=trigger_payout.created_at,
            created_at__lte=instance.created_at,
        ).count()


# -----------------------------
# Service Layer
# -----------------------------


class SignalServiceEngine:
    def __init__(self):
        self.betting_strategy = AutoBetStrategy()
        self.evaluator = SignalEvaluator()

    @staticmethod
    def _cache_key(instance: Multiplier) -> str:
        return CacheKeys.SIGNAL_RECORD.format(instance.worker.id)

    def _update_cache(self, *, data: SignalRecordDict, instance: Multiplier) -> None:
        """Update the cache with new data for the signal record."""
        logger.info(f"Updating signal record: {data}")
        cache.set(self._cache_key(instance), data, 60 * 60 * 24)

    @staticmethod
    def _generate_default_record(instance: Multiplier) -> SignalRecordDict:
        record: SignalRecordDict = {
            "app_name": instance.worker.app,
            "worker_id": str(instance.worker.id),
            "seed_name": instance.worker.name,
            "room_name": get_room_name(
                app=instance.worker.app, worker_name=instance.worker.name
            ),
            "triggered_by_payout_id": None,
            "triggered_at": None,
            "triggered_recently": False,
        }
        return record

    @staticmethod
    def _send_notification(instance: Multiplier) -> None:
        app = instance.worker.app
        subscribers = get_app_subscribers(app)
        room_name = get_room_name(app=app, worker_name=instance.worker.name)

        if not subscribers:
            return

        send_push_notification(
            notification_type=NotificationChannel.PUSH.value,
            title=f"{app} Signal Alert",
            message=f"{room_name} has a strong over 20x chance. Tap to play!",
            user_ids=list(subscribers),
            app_url=AppPageURL.SIGNALS.value,
            collapse_id=NotificationCollapseID.SIGNAL.format(app, room_name),
        )

    def process_latest_payout(self, instance: Multiplier) -> SignalRecordDict:
        """Process the Multiplier instance and return a SignalRecordDict."""
        cache_key = self._cache_key(instance)
        data = cache.get(cache_key) or self._generate_default_record(instance)

        # Extract relevant fields
        triggered_recently = data.get("triggered_recently", False)
        is_betting = data.get("is_betting", False)
        should_send_signal = self.evaluator.should_send_signal(instance)

        if should_send_signal:
            """Logic to trigger a new signal and start betting."""
            logger.info(
                f"Triggering new signal and starting betting session for {data['room_name']}. Triggered by {instance.crash}"
            )
            signal_data = self._generate_default_record(instance)

            metadata: BetMetaData = self.betting_strategy.start()
            metadata.current_payout = float(instance.crash)

            signal_data.update(
                {
                    "triggered_by_payout_id": str(instance.id),
                    "triggered_by_payout": float(instance.crash),
                    "triggered_at": str(instance.created_at),
                    "triggered_recently": True,
                    "is_betting": True,
                    "metadata": asdict(metadata),
                }
            )
            self._send_notification(instance)

        elif triggered_recently and is_betting:
            """Logic to check if we should continue or stop betting."""
            metadata_dict: dict = data.get(
                "metadata"
            )  # If triggered_recently, metadata must exist
            metadata: BetMetaData = BetMetaData(**metadata_dict)

            # Sometimes server restarts so we may have a wrong metadata.current_round. This corrects that.
            metadata.current_round = self.evaluator.count_payouts_since_trigger(
                instance, data.get("triggered_by_payout_id")
            )
            metadata.current_payout = float(instance.crash)

            should_stop_betting = self.betting_strategy.should_stop(
                metadata, float(instance.crash)
            )

            if should_stop_betting:
                """Deactivate the signal and stop betting."""
                logger.info(
                    f"Stop betting session triggered by {instance.crash} for: {data['room_name']}"
                )

                signal_data = data.copy()
                metadata = self.betting_strategy.stop(float(instance.crash), metadata)

                signal_data.update(
                    {
                        "is_betting": False,
                        "stopped_on_payout_id": str(instance.id),
                        "stopped_on_payout": float(instance.crash),
                        "stopped_at": str(instance.created_at),
                        "metadata": asdict(metadata),
                    }
                )

            else:
                """Continue betting."""
                logger.info(
                    f"Continue betting session triggered by {instance.crash} for: {data['room_name']}"
                )
                signal_data = data.copy()
                metadata = self.betting_strategy.place_bet(metadata)
                signal_data["metadata"] = asdict(metadata)

        else:
            """No change. Payout did not trigger signal and no active betting session."""
            signal_data = data

        if self.evaluator.should_reset_trigger(instance) and triggered_recently:
            logger.info(f"Resetting signal record for worker: {data['room_name']}")
            signal_data["triggered_recently"] = False

        self._update_cache(data=signal_data, instance=instance)
        return signal_data

    def __call__(self, instance: Multiplier) -> SignalRecordDict:
        """Make the service callable."""
        return self.process_latest_payout(instance)


signal_service_engine = SignalServiceEngine()


# shared instance
# signal_service = SignalService()

# from __future__ import annotations
#
# from dataclasses import asdict, dataclass, field
# from datetime import timedelta
# from typing import Any, Dict, Optional
#
# from django.core.cache import cache
#
# from analytics.constants import CrashesToMonitor
# from analytics.services import Probability
# from commons.constants import AppPageURL, CacheKeys
# from commons.logger import logger
# from commons.utils import get_room_name, send_push_notification
# from notifications.constants import NotificationChannel
# from observers.models import Multiplier
# from observers.utils import get_app_subscribers
# from uuid import UUID
#
#
# @dataclass()
# class BetMetaData:
#     strategy_name: str  # Name of the strategy
#     initial_bankroll: float  # Initial bankroll
#     bank_roll: float  # Current bankroll
#     current_betting_round: int  # How many times we've bet so far
#     cashout_at: float  # The payout to cash out at
#     stake: int  # The amount to stake per bet
#     max_betting_rounds: int  # Maximum number of betting rounds
#     profit: float
#     loss: float
#
#
# class AutoBetStrategy:
#     name: str = "Autobet"
#     cashout_at: float = 20.0
#     stake: int = 20
#     max_betting_rounds: int = 15
#
#     def has_reached_stop_loss(self, betting_round: int, bank_roll: float) -> bool:
#         """Check if the maximum number of betting rounds has been reached."""
#         has_reached_max_betting_rounds = betting_round >= self.max_betting_rounds
#         bankroll_is_too_low = bank_roll < self.stake
#         return has_reached_max_betting_rounds or bankroll_is_too_low
#
#     def reduce_banking_roll(self, banking_roll: float) -> float:
#         """Reduce the banking roll by the stake amount."""
#         return banking_roll - self.stake
#
#     def is_win(self, payout: float) -> bool:
#         """Check if the bet was won based on the payout."""
#         return payout >= self.cashout_at
#
#     def has_sufficient_bankroll(self, bank_roll: float) -> bool:
#         """Check if there is sufficient bankroll to place the next bet."""
#         return bank_roll >= (self.stake * self.max_betting_rounds)
#
#     def start(self, bank_roll: Optional[float] = None) -> BetMetaData | None:
#         """Initialize betting strategy metadata."""
#         bank_roll = (
#             self.stake * self.max_betting_rounds if bank_roll is None
#             else bank_roll
#         )
#         initial_bankroll = bank_roll
#
#         logger.info(f"Starting {self.name} strategy.")
#         if self.has_sufficient_bankroll(bank_roll):
#             bank_roll = self.reduce_banking_roll(bank_roll)
#             return BetMetaData(
#                 strategy_name=self.name,
#                 bank_roll=bank_roll,
#                 initial_bankroll=initial_bankroll,
#                 current_betting_round=1,
#                 cashout_at=self.cashout_at,
#                 stake=self.stake,
#                 max_betting_rounds=self.max_betting_rounds,
#                 profit=0.0,  # No profit realized on the first bet
#                 loss=self.stake,
#             )
#
#         logger.error(f"Not enough bank roll to start {self.name} strategy")
#         raise ValueError("Insufficient bankroll to start betting strategy.")
#
#     def stop(self, instance: Multiplier, metadata: BetMetaData) -> BetMetaData:
#         """Stop betting strategy and return metadata."""
#         logger.info(f"Stopping {self.name} strategy")
#         payout = float(instance.crash)
#         if self.is_win(payout):
#             profit = self.stake * self.cashout_at
#             metadata.bank_roll += profit
#
#         return metadata
#
#     def place_bet(self, metadata: BetMetaData) -> BetMetaData:
#         """Execute the betting strategy logic."""
#         metadata.bank_roll = self.reduce_banking_roll(metadata.bank_roll)
#         metadata.current_betting_round -= 1
#         metadata.loss -= self.stake
#         return metadata
#
#
# @dataclass
# class SignalRecord:
#     app_name: str
#     worker_id: str
#     seed_name: str
#     room_name: str
#     triggered_by_payout_id: Optional[str] = field(default=None)
#     triggered_at: Optional[str] = field(default=None)
#     stopped_on_payout_id: Optional[str] = field(default=None)
#     stopped_tracking_at: Optional[str] = field(default=None)
#     triggered_recently: bool = field(default=False)
#     metadata: Optional[dict] = field(default_factory=dict)  # To hold BetMetaData as a dict
#
#
# @dataclass(frozen=True)
# class SignalConfig:
#     payout_to_monitor: float = 20.00
#     window_rounds: int = 15
#     redis_ttl_seconds: int = 2 * 60 * 60
#
#
# class SignalServiceEngine:
#     """
#     Stateless service to handle signal processing for Multiplier instances.
#     - No per-call data stored on `self`.
#     - Safe to reuse a single instance across threads/requests.
#     """
#
#     SIGNAL_RECORD_KEY = CacheKeys.SIGNAL_RECORD
#
#     def __init__(
#             self,
#             signal_config: Optional[SignalConfig] = None,
#             betting_strategy: Optional[AutoBetStrategy] = None,  # Only betting strategy supported now
#     ):
#         self.signal_config = signal_config or SignalConfig()
#         self.betting_strategy = betting_strategy or AutoBetStrategy()
#
#     def _cache_key(self, instance: Multiplier) -> str:
#         """
#         Generate a cache key for the signal record based on the worker ID.
#         """
#         return self.SIGNAL_RECORD_KEY.format(instance.worker.id)
#
#     def _generate_default_record_values(self, instance: Multiplier) -> Dict[str, Any]:
#         """
#         Generate default values for a SignalRecord based on the Multiplier instance.
#         """
#         record = SignalRecord(
#             app_name=instance.worker.app,
#             worker_id=str(instance.worker.id),
#             seed_name=instance.worker.name,
#             room_name=get_room_name(app=instance.worker.app, worker_name=instance.worker.name),
#             triggered_by_payout_id=None,
#             triggered_at=None,
#             triggered_recently=False,
#         )
#         return asdict(record)
#
#     def _update_cache(self, *, data: dict, instance: Multiplier) -> None:
#         """Update the cache with new data for the signal record."""
#         cache.set(
#             self._cache_key(instance),
#             data,
#             self.signal_config.redis_ttl_seconds,
#         )
#
#     def _low_streak_is_close(self, instance: Multiplier) -> bool:
#         """
#         True if, within the last 60 minutes, there are at least 7 payouts >= threshold,
#         and the two OLDEST among those 7 occurred <= 8 minutes apart.
#         """
#         time_now = instance.created_at
#         window_start = time_now - timedelta(hours=1)
#         very_close_minutes = 8
#
#         qs = (
#             Multiplier.objects
#             .filter(
#                 worker=instance.worker,
#                 created_at__gte=window_start,
#                 created_at__lte=time_now,
#                 crash__gte=self.signal_config.payout_to_monitor,
#             )
#             .order_by('-created_at')  # most recent first
#             .values_list('created_at', flat=True)
#         )
#
#         # Grab only the 6th and 7th most recent (i.e., the two oldest among the top seven)
#         oldest_two = list(qs[5:7])  # OFFSET 5 LIMIT 2 at the DB level
#         if len(oldest_two) < 2:  # fewer than 7 total in window
#             return False
#
#         # In desc order, index 5 is newer than index 6 → subtract yields non-negative gap
#         gap = oldest_two[0] - oldest_two[1]
#         return gap <= timedelta(minutes=very_close_minutes)
#
#     def _has_low_streak(self, instance: Multiplier) -> bool:
#         """
#         Check if there were less than x over 20x payouts in the last 60 minutes.
#         """
#         time_now = instance.created_at
#         one_hour_ago = time_now - timedelta(hours=1)
#         max_high_payouts_count = 6
#
#         high_payouts_count = Multiplier.objects.filter(
#             worker=instance.worker,
#             created_at__lte=time_now,
#             created_at__gte=one_hour_ago,
#             crash__gte=self.signal_config.payout_to_monitor,
#         ).count()
#         return high_payouts_count <= max_high_payouts_count
#
#     def _probability_is_high(self, instance: Multiplier) -> bool:
#         """
#         Check if the probability of a payout is >= 80%.
#         """
#         high_probability: float = 80.00
#         probability = Probability.calculate_probability(
#             worker_id=str(instance.worker.id), crash=CrashesToMonitor.OVER_20X.value
#         )
#         return probability >= high_probability
#
#     def _has_been_triggered_recently(self, instance: Multiplier) -> bool:
#         data = cache.get(self._cache_key(instance)) or {}
#         return bool(data.get("triggered_recently", False))
#
#     def _deactivate_signal_record(self, instance: Multiplier, data: dict) -> dict:
#         """Mark the signal record as inactive."""
#         data["triggered_recently"] = False
#         data["stopped_tracking_at"] = str(instance.created_at)
#         return data
#
#     def _send_notification(self, instance: Multiplier) -> None:
#         app = instance.worker.app
#         room_name = get_room_name(app=app, worker_name=instance.worker.name)
#         title = f"{app} Signal Alert"
#         message = f"{app} {room_name} has a strong over 20x chance. Tap to play!"
#
#         subscribers = get_app_subscribers(app)
#         if not subscribers:
#             logger.info(f"No subscribers found for {app}.")
#             return
#
#         try:
#             logger.info("Found %d subscribers for %s.", len(subscribers), app)
#             send_push_notification(
#                 notification_type=NotificationChannel.PUSH.value,
#                 title=title,
#                 message=message,
#                 user_ids=list(subscribers),
#                 app_url=AppPageURL.SIGNALS.value,
#             )
#         except Exception as e:
#             logger.error("Failed to enqueue push for %s -> %s", app, e)
#
#     def _get_rounds_passed(
#             self, *, instance: Multiplier, trigger_id: str, worker_id: str
#     ) -> int:
#         """
#         Calculate how many rounds have passed since the signal was triggered.
#         """
#         trigger_payout = Multiplier.objects.get(id=trigger_id)
#         rounds_passed = Multiplier.objects.filter(
#             worker__id=worker_id,
#             created_at__gt=trigger_payout.created_at,
#             created_at__lte=instance.created_at,
#         ).count()
#
#         return rounds_passed
#
#     def _trigger_signal(self, instance: Multiplier) -> Dict[str, Any]:
#         """Create a record for a triggered signal"""
#         logger.info(
#             "Triggering signal for %s %s", instance.worker.app, instance.worker.name
#         )
#
#         record = SignalRecord(
#             app_name=instance.worker.app,
#             worker_id=str(instance.worker.id),
#             seed_name=instance.worker.name,
#             room_name=get_room_name(app=instance.worker.app, worker_name=instance.worker.name),
#             triggered_by_payout_id=str(instance.id),
#             triggered_at=str(instance.created_at),
#             triggered_recently=True,
#         )
#
#         return asdict(record)
#
#     def _should_send_signal(self, instance: Multiplier) -> bool:
#         """
#         Determine if a signal should be sent based on payout conditions.
#         """
#         return (
#                 (
#                         self._has_low_streak(instance) or self._low_streak_is_close(instance)
#                 )
#                 and self._probability_is_high(instance)
#                 and not self._has_been_triggered_recently(instance)
#         )
#
#     def _reset_signal(self, instance: Multiplier) -> Dict[str, Any]:
#         """Reset the signal record for a worker instance."""
#         logger.info(
#             "Resetting signal record for worker: %s %s",
#             instance.worker.app,
#             instance.worker.name,
#         )
#         cache_key = self._cache_key(instance)
#         defaults = self._generate_default_record_values(instance)
#
#         current = cache.get(cache_key) or {}
#         current.update(defaults)  # prioritize reset/default values
#
#         record = SignalRecord(**current)
#         cache.set(cache_key, asdict(record), self.signal_config.redis_ttl_seconds)
#         return asdict(record)
#
#     def process_latest_payout(self, instance: Multiplier) -> Dict[str, Any] | None:
#         """
#         Process the Multiplier instance and return a SignalRecord if applicable.
#         """
#         payout = float(instance.crash)
#         threshold = self.signal_config.payout_to_monitor
#         cache_key = self._cache_key(instance)
#         data = cache.get(
#             cache_key
#         ) or self._generate_default_record_values(instance)
#         metadata: BetMetaData = data.get("metadata", {})
#         is_active = self._has_been_triggered_recently(instance)
#
#         rounds_played = self._get_rounds_passed(
#             instance=instance,
#             trigger_id=data.get("triggered_by_payout_id"),
#             worker_id=data.get("worker_id"),
#         )
#         has_reached_stop_loss = self.betting_strategy.has_reached_stop_loss(
#             betting_round=rounds_played,
#             bank_roll=metadata.get("bank_roll", 0.0)
#         )
#         has_won = self.betting_strategy.is_win(payout)
#
#         should_stop_betting = (
#                 is_active and (has_reached_stop_loss or has_won)
#         )
#
#         if self._should_send_signal(instance):
#             """Logic to trigger a new signal and start betting."""
#             signal_record = self._trigger_signal(instance)  # Trigger a new signal
#             metadata: BetMetaData = self.betting_strategy.start()
#
#             signal_record.metadata = asdict(metadata)
#             cache_key = self._cache_key(instance)
#             cache.set(cache_key, signal_record, self.signal_config.redis_ttl_seconds)
#
#             self._send_notification(instance)
#
#             return signal_record
#
#         elif should_stop_betting:
#             """Logic to stop betting and deactivate the signal."""
#             self._deactivate_signal_record(instance, data)
#             metadata = self.betting_strategy.stop(metadata)
#             data["metadata"] = asdict(metadata)
#
#         elif is_active:
#             """Update the signal record if still active."""
#             metadata = self.betting_strategy.place_bet(metadata)
#             data["metadata"] = asdict(metadata)
#
#         else:
#             pass
#
#         self._update_cache(data=data, instance=instance)
#         return data
#
#     def __call__(self, instance: Multiplier) -> Dict[str, Any] | None:
#         """
#         Make the service callable to process a Multiplier instance.
#         """
#         return self.process_latest_payout(instance)
#
#
# signal_service_engine = SignalServiceEngine()
