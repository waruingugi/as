from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

from django.core.cache import cache

from commons.constants import CacheKeys
from commons.logger import logger
from commons.tasks import send_push_task
from commons.utils import get_room_name
from notifications.constants import NotificationChannel
from observers.models import Multiplier
from observers.utils import get_app_subscribers


@dataclass
class SignalRecord:
    """
    A class to represent a signal record.
    This is a placeholder for the actual implementation.
    """

    app_name: str
    worker_id: str
    seed_name: str
    triggered_by_payout_id: str | None = field(default=None)
    triggered_at: datetime | None = field(default=None)
    remaining_rounds: int = field(default=0)
    profit_window_rounds: int = field(default=15)
    triggered_recently: bool = field(default=False)


@dataclass(frozen=True)
class SignalConfig:
    payout_to_monitor: float = (
        20.00  # The payout we're interesed in monitoring, e.g., 20×
    )
    min_payouts_in_cluster: int = (
        7  # minimum payouts in the last 60 minutes with multiplier ≥ 20×
    )
    max_rounds: int = 4  # Max rounds since last ≥20×
    huge_payout: float = 80.00  # Size of payout to be considered "huge"
    burst_rounds: int = 20  # Lookback 20 rounds for burst
    min_payouts_in_bust: int = 3  # Number of ≥20× payout needed in last burst rounds
    window_rounds: int = 15  # rounds to watch after we send a signal

    # Redis fallback TTL (seconds) to auto-clean the cooldown key in case
    # a process dies. 2 hours is plenty for a 15-round window in practice.
    redis_ttl_seconds: int = 2 * 60 * 60


class SignalEngineService:
    """
    A service class that provides access to the signal engine.
    """

    SIGNAL_RECORD_KEY = CacheKeys.SIGNAL_RECORD

    def __init__(self):
        self.instance = None
        self.signal_config = SignalConfig()

    def _generate_default_record_values(self) -> dict:
        """
        Generate a new signal record with default values.
        This is used to reset the signal engine.
        """
        signal_record = SignalRecord(
            app_name=self.instance.worker.app,
            worker_id=str(self.instance.worker.id),
            seed_name=self.instance.worker.name,
            triggered_by_payout_id=None,
            triggered_at=None,
            remaining_rounds=self.signal_config.window_rounds,
            profit_window_rounds=self.signal_config.window_rounds,
            triggered_recently=False,
        )
        return asdict(signal_record)

    def _has_cluster(self) -> bool:
        """
        Check if in the past 60 minutes, there were at least 7 payouts with a multiplier of ≥ 20x.
        This indicates a busy hour with significant activity.
        It helps identify clusters of high payouts, suggesting a favorable environment for big wins.
        """

        time_now = self.instance.created_at
        one_hour_ago = time_now - timedelta(hours=1)
        # Fetch payouts in the last 60 minutes with multiplier ≥ 20
        high_payouts_count = Multiplier.objects.filter(
            worker=self.instance.worker,
            created_at__lte=self.instance.created_at,
            created_at__gte=one_hour_ago,
            crash__gte=self.signal_config.payout_to_monitor,
        ).count()

        return high_payouts_count >= self.signal_config.min_payouts_in_cluster

    def _has_short_streak(self) -> bool:
        """
        Check if either the last ≥20× was very recent (≤ 4 rounds ago) or it was huge (≥ 80×).
        """
        # Step 1: Find the last ≥20× payout
        last_high20 = (
            Multiplier.objects.filter(
                worker=self.instance.worker,
                created_at_lte=self.instance.created_at,
                crash__gte=self.signal_config.payout_to_monitor,
            )
            .order_by("-created_at")
            .first()
        )

        if not last_high20:
            return False

        # Step 2: Count the number of rounds between last_high20 and current payout
        rounds_since_last_high20 = Multiplier.objects.filter(
            worker=self.instance.worker,
            created_at__gt=last_high20.created_at,
            created_at__lte=self.instance.created_at,
        ).count()

        # Step 3: Check if it was recent
        is_recent = rounds_since_last_high20 <= self.signal_config.max_rounds

        # Step 4: last_high20_multiplier >= 80
        is_huge_payout = float(last_high20) >= self.signal_config.huge_payout

        return is_recent or is_huge_payout

    def _has_short_burst(self) -> bool:
        """
        Check if in the last 20 rounds, there were at least 3 payouts ≥ 20×.
        """
        # Get the last 20 payouts including the current one
        last_20 = Multiplier.objects.filter(
            worker=self.instance.worker, created_at__lte=self.instance.created_at
        ).order_by(  # Includes the current round but locked for real time calculations
            "-created_at"
        )[: self.signal_config.burst_rounds]

        # Count how many have crash ≥ 20
        high20_count = sum(
            float(payout.crash) >= self.signal_config.payout_to_monitor
            for payout in last_20
        )

        return high20_count >= self.signal_config.min_payouts_in_bust

    def _has_been_triggered_recently(self) -> bool:
        """
        Check if the signal has been triggered recently.
        This prevents sending multiple signals in a short time frame.
        """
        cache_key = self.SIGNAL_RECORD_KEY.format(self.instance.worker.id)
        signal_record_data = cache.get(cache_key)
        return signal_record_data.get("triggered_recently", False)

    def _should_send_signal(self) -> bool:
        """
        Run all checks to determine if the signal engine should be active.
        """
        return (
            self._has_cluster()
            and self._has_short_streak()
            and self._has_short_burst()
            and not self._has_been_triggered_recently()
        )

    def _update_signal(self) -> dict | None:
        """
        Update the signal engine with a new signal record.
        Decrements the remaining_rounds for the signal record in the cache by 1.
        """
        logger.info(
            f"Updating signal record for worker: {self.instance.worker.app} {self.instance.worker.name}"
        )
        cache_key = self.SIGNAL_RECORD_KEY.format(self.instance.worker.id)
        signal_record_data = (
            cache.get(cache_key) or self._generate_default_record_values()
        )

        # Calculate remaining_rounds based on rounds since trigger payout
        trigger_id = signal_record_data.get("triggered_by_payout_id")
        worker_id = signal_record_data.get("worker_id")

        trigger_payout = Multiplier.objects.get(id=trigger_id)
        rounds_passed = Multiplier.objects.filter(  # Count rounds since trigger payout
            worker__id=worker_id,
            created_at__gt=trigger_payout.created_at,
            created_at__lte=self.instance.created_at,
        ).count()
        remaining = max(  # Calculate remaining rounds
            0, self.signal_config.window_rounds - rounds_passed
        )

        signal_record_data["remaining_rounds"] = remaining
        updated_signal_record = SignalRecord(**signal_record_data)
        cache.set(
            cache_key,
            asdict(updated_signal_record),
            self.signal_config.redis_ttl_seconds,
        )
        return asdict(updated_signal_record)

    def _reset_signal(self) -> dict:
        """Update the status of the signal record"""
        logger.info(
            f"Resetting signal record for worker: {self.instance.worker.app} {self.instance.worker.name}"
        )
        cache_key = self.SIGNAL_RECORD_KEY.format(self.instance.worker.id)

        default_values = self._generate_default_record_values()

        signal_record_data = cache.get(cache_key) or {}
        # Merge existing data with defaults, prioritizing reset values
        signal_record_data.update(default_values)
        signal_record = SignalRecord(**signal_record_data)

        cache.set(
            cache_key, asdict(signal_record), self.signal_config.redis_ttl_seconds
        )
        return asdict(signal_record)

    def _trigger_signal(self) -> dict:
        """
        Trigger the signal engine with a new signal record.
        Stores the signal record in cache and returns it.
        """
        logger.info(
            f"Triggering signal for {self.instance.worker.app} {self.instance.worker.name}"
        )
        cache_key = self.SIGNAL_RECORD_KEY.format(self.instance.worker.id)
        signal_record = SignalRecord(
            app_name=self.instance.worker.app,
            worker_id=str(self.instance.worker.id),
            seed_name=self.instance.worker.name,
            triggered_by_payout_id=str(
                self.instance.id
            ),  # Use the current instance ID as the trigger payout ID
            triggered_at=self.instance.created_at.isoformat(),
            remaining_rounds=self.signal_config.window_rounds,
            profit_window_rounds=self.signal_config.window_rounds,
            triggered_recently=True,
        )
        cache.set(
            cache_key, asdict(signal_record), self.signal_config.redis_ttl_seconds
        )
        return asdict(signal_record)

    def _send_notification(self, signal_record: dict) -> None:
        """
        Send a push notification about the triggered signal.
        """
        """Build and dispatch a push notification for a threshold crossing."""
        app = self.instance.worker.app
        room_name = get_room_name(app=app, worker_name=self.instance.worker.name)
        title = f"{app} Signal Alert"
        message = f"{app} {room_name} has a strong over 20x chance. Tap to play!"

        subscribers = get_app_subscribers(app)
        if not subscribers:
            logger.info(f"No subscribers found for {app}.")
            return

        try:
            logger.info(f"Found {len(subscribers)} subscribers for {app}.")
            # schedule background task
            send_push_task.delay(
                notification_type=NotificationChannel.PUSH.value,
                title=title,
                message=message,
                user_ids=list(subscribers),
            )
        except Exception as e:
            logger.error(f"Failed to enqueue push for {app} -> {e}")

    def process_latest_payout(self, instance: Multiplier) -> dict | None:
        self.instance = instance

        payout = float(self.instance.crash)
        threshold = self.signal_config.payout_to_monitor

        if payout >= threshold:
            # Reset the signal engine if the payout is greater than or equal to the threshold
            return self._reset_signal()

        elif self._should_send_signal():
            signal_record = self._trigger_signal()
            self._send_notification(signal_record)
            return signal_record
        else:
            return self._update_signal()
