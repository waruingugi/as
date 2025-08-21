from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import timedelta
from typing import Any, Dict, Optional

from django.core.cache import cache

from analytics.constants import CrashesToMonitor
from analytics.services import Probability
from commons.constants import AppPageURL, CacheKeys
from commons.logger import logger
from commons.utils import get_room_name, send_push_notification
from notifications.constants import NotificationChannel
from observers.models import Multiplier
from observers.utils import get_app_subscribers

# @dataclass
# class SignalRecord:
#     app_name: str
#     worker_id: str
#     seed_name: str
#     triggered_by_payout_id: Optional[str] = field(default=None)
#     triggered_at: Optional[str] = field(default=None)
#     remaining_rounds: int = field(default=0)
#     profit_window_rounds: int = field(default=15)
#     triggered_recently: bool = field(default=False)
#
#
# @dataclass(frozen=True)
# class SignalConfig:
#     payout_to_monitor: float = 20.00
#     min_payouts_in_cluster: int = 7
#     max_rounds: int = 4
#     huge_payout: float = 80.00
#     burst_rounds: int = 20
#     min_payouts_in_bust: int = 3
#     window_rounds: int = 15
#     redis_ttl_seconds: int = 2 * 60 * 60  # 2 hours


# class SignalEngineService:
#     """
#     Stateless service:
#     - No per-call data stored on `self`.
#     - Safe to reuse a single instance across threads/requests.
#     """
#
#     SIGNAL_RECORD_KEY = CacheKeys.SIGNAL_RECORD  # e.g. "signal_record:{0}"
#
#     def __init__(self, signal_config: Optional[SignalConfig] = None):
#         self.signal_config = signal_config or SignalConfig()
#
#     # ---------- helpers (all accept `instance`) ----------
#
#     def _cache_key(self, instance: Multiplier) -> str:
#         return self.SIGNAL_RECORD_KEY.format(instance.worker.id)
#
#     def _generate_default_record_values(self, instance: Multiplier) -> Dict[str, Any]:
#         record = SignalRecord(
#             app_name=instance.worker.app,
#             worker_id=str(instance.worker.id),
#             seed_name=instance.worker.name,
#             triggered_by_payout_id=None,
#             triggered_at=None,
#             remaining_rounds=self.signal_config.window_rounds,
#             profit_window_rounds=self.signal_config.window_rounds,
#             triggered_recently=False,
#         )
#         return asdict(record)
#
#     def _has_cluster(self, instance: Multiplier) -> bool:
#         """Check if there were >=7 over 20x payouts in the past 60 minutes."""
#         time_now = instance.created_at
#         one_hour_ago = time_now - timedelta(hours=1)
#
#         high_payouts_count = (
#             Multiplier.objects.filter(
#                 worker=instance.worker,
#                 created_at__lte=time_now,
#                 created_at__gte=one_hour_ago,
#                 crash__gte=self.signal_config.payout_to_monitor,
#             ).count()
#         )
#         return high_payouts_count >= self.signal_config.min_payouts_in_cluster
#
#     def _has_short_streak(self, instance: Multiplier) -> bool:
#         """
#         Check if there was a large payout in the last 20 rounds or any over 20x payout happened very recently.
#         """
#         last_high20 = (
#             Multiplier.objects.filter(
#                 worker=instance.worker,
#                 created_at__lte=instance.created_at,  # (fixed typo: __lte)
#                 crash__gte=self.signal_config.payout_to_monitor,
#             )
#             .order_by("-created_at")
#             .first()
#         )
#         if not last_high20:
#             return False
#
#         rounds_since_last_high20 = Multiplier.objects.filter(
#             worker=instance.worker,
#             created_at__gt=last_high20.created_at,
#             created_at__lte=instance.created_at,
#         ).count()
#
#         is_recent = rounds_since_last_high20 <= self.signal_config.max_rounds
#         is_huge_payout = float(last_high20.crash) >= self.signal_config.huge_payout  # (fixed)
#
#         return is_recent or is_huge_payout
#
#     def _has_short_burst(self, instance: Multiplier) -> bool:
#         """In the last 20 rounds, at least 3 payouts ≥ 20×."""
#         last_20 = (
#             Multiplier.objects.filter(
#                 worker=instance.worker, created_at__lte=instance.created_at
#             )
#             .order_by("-created_at")[: self.signal_config.burst_rounds]
#         )
#         high20_count = sum(
#             float(p.crash) >= self.signal_config.payout_to_monitor for p in last_20
#         )
#         return high20_count >= self.signal_config.min_payouts_in_bust
#
#     def _has_been_triggered_recently(self, instance: Multiplier) -> bool:
#         data = cache.get(self._cache_key(instance)) or {}
#         return bool(data.get("triggered_recently", False))
#
#     def _should_send_signal(self, instance: Multiplier) -> bool:
#         return (
#             self._has_cluster(instance)
#             and self._has_short_streak(instance)
#             and self._has_short_burst(instance)
#             and not self._has_been_triggered_recently(instance)
#         )
#
#     def _update_signal(self, instance: Multiplier) -> Dict[str, Any] | None:
#         """
#         Decrement remaining rounds since the trigger payout.
#         If there's no trigger stored yet or was not triggered recently, do nothing.
#         """
#         logger.info(
#             "Updating signal record for worker: %s %s",
#             instance.worker.app,
#             instance.worker.name,
#         )
#         cache_key = self._cache_key(instance)
#         signal_record_data = cache.get(cache_key) or self._generate_default_record_values(instance)
#
#         triggered_recently = signal_record_data.get("triggered_recently", False)
#
#         if triggered_recently:
#             trigger_id = signal_record_data.get("triggered_by_payout_id")
#             worker_id = signal_record_data.get("worker_id")
#
#             trigger_payout = Multiplier.objects.get(id=trigger_id)
#             rounds_passed = Multiplier.objects.filter(
#                 worker__id=worker_id,
#                 created_at__gt=trigger_payout.created_at,
#                 created_at__lte=instance.created_at,
#             ).count()
#
#             remaining = max(0, self.signal_config.window_rounds - rounds_passed)
#             signal_record_data["remaining_rounds"] = remaining
#
#             updated_signal_record = SignalRecord(**signal_record_data)
#             cache.set(cache_key, asdict(updated_signal_record), self.signal_config.redis_ttl_seconds)
#             return asdict(updated_signal_record)
#
#         return signal_record_data
#
#     def _reset_signal(self, instance: Multiplier) -> Dict[str, Any]:
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
#     def _trigger_signal(self, instance: Multiplier) -> Dict[str, Any]:
#         logger.info(
#             "Triggering signal for %s %s", instance.worker.app, instance.worker.name
#         )
#         cache_key = self._cache_key(instance)
#         record = SignalRecord(
#             app_name=instance.worker.app,
#             worker_id=str(instance.worker.id),
#             seed_name=instance.worker.name,
#             triggered_by_payout_id=str(instance.id),
#             triggered_at=str(instance.created_at),
#             remaining_rounds=self.signal_config.window_rounds,
#             profit_window_rounds=self.signal_config.window_rounds,
#             triggered_recently=True,
#         )
#         cache.set(cache_key, asdict(record), self.signal_config.redis_ttl_seconds)
#         return asdict(record)
#
#     def _send_notification(self, instance: Multiplier) -> None:
#         app = instance.worker.app
#         room_name = get_room_name(app=app, worker_name=instance.worker.name)
#         title = f"{app} Signal Alert"
#         message = f"{app} {room_name} has a strong over 20x chance. Tap to play!"
#
#         subscribers = get_app_subscribers(app)
#         if not subscribers:
#             logger.info("No subscribers found for %s.", app)
#             return
#
#         try:
#             logger.info("Found %d subscribers for %s.", len(subscribers), app)
#             send_push_task.delay(
#                 notification_type=NotificationChannel.PUSH.value,
#                 title=title,
#                 message=message,
#                 user_ids=list(subscribers),
#             )
#         except Exception as e:
#             logger.error("Failed to enqueue push for %s -> %s", app, e)
#
#     # ---------- public API ----------
#
#     def process_latest_payout(self, instance: Multiplier) -> Dict[str, Any] | None:
#         payout = float(instance.crash)
#         threshold = self.signal_config.payout_to_monitor
#
#         if payout >= threshold:
#             # Large payout: reset the engine window
#             return self._reset_signal(instance)
#
#         if self._should_send_signal(instance):
#             signal_record = self._trigger_signal(instance)
#             self._send_notification(instance)
#             return signal_record
#
#         return self._update_signal(instance)
#
#     def __call__(self, instance: Multiplier) -> Dict[str, Any] | None:
#         return self.process_latest_payout(instance)
#
#
# signal_engine_service = SignalEngineService()


@dataclass
class SignalRecord:
    app_name: str
    worker_id: str
    seed_name: str
    triggered_by_payout_id: Optional[str] = field(default=None)
    triggered_at: Optional[str] = field(default=None)
    remaining_rounds: int = field(default=0)
    profit_window_rounds: int = field(default=15)
    triggered_recently: bool = field(default=False)


@dataclass(frozen=True)
class SignalConfig:
    payout_to_monitor: float = 20.00
    window_rounds: int = 15
    redis_ttl_seconds: int = 2 * 60 * 60


class SignalServiceEngine:
    """
    Stateless service to handle signal processing for Multiplier instances.
    - No per-call data stored on `self`.
    - Safe to reuse a single instance across threads/requests.
    """

    SIGNAL_RECORD_KEY = CacheKeys.SIGNAL_RECORD

    def __init__(self, signal_config: Optional[SignalConfig] = None):
        self.signal_config = signal_config or SignalConfig()

    def _cache_key(self, instance: Multiplier) -> str:
        """
        Generate a cache key for the signal record based on the worker ID.
        """
        return self.SIGNAL_RECORD_KEY.format(instance.worker.id)

    def _generate_default_record_values(self, instance: Multiplier) -> Dict[str, Any]:
        """
        Generate default values for a SignalRecord based on the Multiplier instance.
        """
        record = SignalRecord(
            app_name=instance.worker.app,
            worker_id=str(instance.worker.id),
            seed_name=instance.worker.name,
            triggered_by_payout_id=None,
            triggered_at=None,
            remaining_rounds=self.signal_config.window_rounds,
            profit_window_rounds=self.signal_config.window_rounds,
            triggered_recently=False,
        )
        return asdict(record)

    def _has_low_streak(self, instance: Multiplier) -> bool:
        """
        Check if there were less than x over 20x payouts in the last 60 minutes.
        """
        time_now = instance.created_at
        one_hour_ago = time_now - timedelta(hours=1)
        max_high_payouts_count = 7

        high_payouts_count = Multiplier.objects.filter(
            worker=instance.worker,
            created_at__lte=time_now,
            created_at__gte=one_hour_ago,
            crash__gte=self.signal_config.payout_to_monitor,
        ).count()
        return high_payouts_count <= max_high_payouts_count

    def _probability_is_high(self, instance: Multiplier) -> bool:
        """
        Check if the probability of a payout is >= 80%.
        """
        high_probability: float = 80.00
        probability = Probability.calculate_probability(
            worker_id=str(instance.worker.id), crash=CrashesToMonitor.OVER_20X.value
        )
        return probability >= high_probability

    def _has_been_triggered_recently(self, instance: Multiplier) -> bool:
        data = cache.get(self._cache_key(instance)) or {}
        return bool(data.get("triggered_recently", False))

    def _send_notification(self, instance: Multiplier) -> None:
        app = instance.worker.app
        room_name = get_room_name(app=app, worker_name=instance.worker.name)
        title = f"{app} Signal Alert"
        message = f"{app} {room_name} has a strong over 20x chance. Tap to play!"

        subscribers = get_app_subscribers(app)
        if not subscribers:
            logger.info("No subscribers found for %s.", app)
            return

        try:
            logger.info("Found %d subscribers for %s.", len(subscribers), app)
            send_push_notification(
                notification_type=NotificationChannel.PUSH.value,
                title=title,
                message=message,
                user_ids=list(subscribers),
                app_url=AppPageURL.SIGNALS.value,
            )
        except Exception as e:
            logger.error("Failed to enqueue push for %s -> %s", app, e)

    def _update_signal(self, instance: Multiplier) -> Dict[str, Any] | None:
        """
        Decrement remaining rounds since the trigger payout.
        If there's no trigger stored yet or was not triggered recently, do nothing.
        """
        logger.info(
            "Updating signal record for worker: %s %s",
            instance.worker.app,
            instance.worker.name,
        )
        cache_key = self._cache_key(instance)
        signal_record_data = cache.get(
            cache_key
        ) or self._generate_default_record_values(instance)

        triggered_recently = signal_record_data.get("triggered_recently", False)

        if triggered_recently:
            trigger_id = signal_record_data.get("triggered_by_payout_id")
            worker_id = signal_record_data.get("worker_id")

            trigger_payout = Multiplier.objects.get(id=trigger_id)
            rounds_passed = Multiplier.objects.filter(
                worker__id=worker_id,
                created_at__gt=trigger_payout.created_at,
                created_at__lte=instance.created_at,
            ).count()

            remaining = max(0, self.signal_config.window_rounds - rounds_passed)
            signal_record_data["remaining_rounds"] = remaining

            updated_signal_record = SignalRecord(**signal_record_data)
            cache.set(
                cache_key,
                asdict(updated_signal_record),
                self.signal_config.redis_ttl_seconds,
            )
            return asdict(updated_signal_record)

        return signal_record_data

    def _trigger_signal(self, instance: Multiplier) -> Dict[str, Any]:
        """Create a record for a triggered signal"""
        logger.info(
            "Triggering signal for %s %s", instance.worker.app, instance.worker.name
        )
        cache_key = self._cache_key(instance)
        record = SignalRecord(
            app_name=instance.worker.app,
            worker_id=str(instance.worker.id),
            seed_name=instance.worker.name,
            triggered_by_payout_id=str(instance.id),
            triggered_at=str(instance.created_at),
            remaining_rounds=self.signal_config.window_rounds,
            profit_window_rounds=self.signal_config.window_rounds,
            triggered_recently=True,
        )
        cache.set(cache_key, asdict(record), self.signal_config.redis_ttl_seconds)
        return asdict(record)

    def _should_send_signal(self, instance: Multiplier) -> bool:
        """
        Determine if a signal should be sent based on payout conditions.
        """
        return (
            self._has_low_streak(instance)
            and self._probability_is_high(instance)
            and not self._has_been_triggered_recently(instance)
        )

    def _reset_signal(self, instance: Multiplier) -> Dict[str, Any]:
        """Reset the signal record for a worker instance."""
        logger.info(
            "Resetting signal record for worker: %s %s",
            instance.worker.app,
            instance.worker.name,
        )
        cache_key = self._cache_key(instance)
        defaults = self._generate_default_record_values(instance)

        current = cache.get(cache_key) or {}
        current.update(defaults)  # prioritize reset/default values

        record = SignalRecord(**current)
        cache.set(cache_key, asdict(record), self.signal_config.redis_ttl_seconds)
        return asdict(record)

    def process_latest_payout(self, instance: Multiplier) -> Dict[str, Any] | None:
        """
        Process the Multiplier instance and return a SignalRecord if applicable.
        """
        payout = float(instance.crash)
        threshold = self.signal_config.payout_to_monitor
        if payout >= threshold:
            return self._reset_signal(instance)

        elif self._should_send_signal(instance):
            signal_record = self._trigger_signal(instance)
            self._send_notification(instance)
            return signal_record

        return self._update_signal(instance)

    def __call__(self, instance: Multiplier) -> Dict[str, Any] | None:
        """
        Make the service callable to process a Multiplier instance.
        """
        return self.process_latest_payout(instance)


signal_service_engine = SignalServiceEngine()
