from collections import defaultdict

from django.core.cache import cache

from commons.constants import (
    DEFAULT_CACHE_DURATION,
    MULTIPLIER_PAGE_SIZE,
    SIGNAL_NOTIFICATION_TRIGGERS,
    BettingApp,
    CacheKeys,
)
from commons.logger import logger
from notifications.constants import (
    NotificationChannel,
)
from notifications.push import OneSignal
from observers.models import Multiplier
from workers.models import Worker


def get_new_multipliers(
    worker_id: str, new_multipliers_list: list[float]
) -> list[float]:
    """Perform sequence matching between two lists to find new payouts"""
    sequence_length = len(new_multipliers_list)

    previous_multipliers = (
        Multiplier.objects.filter(worker_id=worker_id)
        .values_list("crash", flat=True)
        .order_by("-created_at")[:sequence_length]
    )
    previous_multiplier_list = [float(payout) for payout in previous_multipliers]

    for i in range(sequence_length):
        if (
            new_multipliers_list[i:]
            == previous_multiplier_list[: (sequence_length - i)]
        ):
            return new_multipliers_list[:i]

    return new_multipliers_list


def refresh_worker_crash_query(instances) -> None:
    worker_ids = {instance.worker_id for instance in instances}
    for worker_id in worker_ids:
        get_worker_crash_list(worker_id, MULTIPLIER_PAGE_SIZE)


def get_worker_crash_list(worker_id: str, count: int) -> list:
    """
    Fetch the last `count` crashes for a worker from the database.
    """
    logger.info(f"Get worker crash list for worker:{worker_id} with count:{count}")
    multipliers_qs = Multiplier.objects.filter(worker_id=worker_id).order_by(
        "-created_at"
    )[:count]

    crash_list = [
        {
            "created_at": m.created_at,
            "crash": m.crash,
        }
        for m in multipliers_qs
    ]

    cache_key = CacheKeys.WORKER_CRASH_QUERY.format(worker_id)
    cache.set(cache_key, crash_list, DEFAULT_CACHE_DURATION)

    return crash_list


def get_workers_crash_history(
    app: str, count: int = MULTIPLIER_PAGE_SIZE, recompute: bool = False
) -> list:
    logger.info(f"Get workers crash history for app:{app} with count:{count}")
    workers = Worker.objects.filter(app=app)
    if not workers.exists():  # Handle empty queryset
        return []

    data = []
    for worker in workers:
        if recompute:
            crash_list = get_worker_crash_list(worker.id, count)  # type: ignore

        else:
            logger.info(f"Get cached worker crash list for worker:{worker.id}")
            cache_key = CacheKeys.WORKER_CRASH_QUERY.format(worker.id)
            crash_list = cache.get(cache_key)
            if crash_list is None:
                crash_list = get_worker_crash_list(worker.id, count)  # type: ignore

        data.append({"id": worker.id, "name": worker.name, "crash": crash_list})

    return data


def get_app_threshold_subscribers(app: str, threshold: int) -> set:
    """
    Get the subscribers for a specific app and threshold.
    """
    cache_key = cache.get(CacheKeys.USERS_SIGNAL_SETTINGS, {})
    subscribers = cache_key.get(app, {}).get(threshold, set())
    return subscribers


class SignalNotificationMonitor:
    """
    Monitor for signal notifications.
    """

    RESET_AT_TRIGGER = 50
    TRIGGER_SIGNAL_CACHE_TIMEOUT = None  # Cache never expires
    TRIGGER_CACHE_KEY = CacheKeys.TRIGGER_SIGNAL_FLAGS
    THRESHOLDS = SIGNAL_NOTIFICATION_TRIGGERS

    def _batch_reset_trigger_flags(self) -> None:
        """
        Reset all trigger signal flags for all apps and thresholds.
        """
        trigger_signal_flags = defaultdict(dict)
        for app in BettingApp.list():
            for threshold in self.THRESHOLDS:
                trigger_signal_flags[app][threshold] = {
                    "triggered": False,  # Has the signal been triggered?
                    "triggered_at": None,  # Time the signal was triggered
                    "triggered_by": None,  # The payout that triggered the signal
                }
        self._set_trigger_signal_flags(trigger_signal_flags)

    def _get_trigger_signal_flags(self) -> dict:
        """
        Get the current signal trigger flags from cache.
        If not present, initialize them.
        """
        cached = cache.get(self.TRIGGER_CACHE_KEY, {})
        if not cached:
            self._batch_reset_trigger_flags()
            cached = cache.get(self.TRIGGER_CACHE_KEY, {})
        return cached

    def _set_trigger_signal_flags(self, trigger_signal_flags: dict) -> None:
        """
        Set the current signal trigger flags in cache.
        """
        cache.set(
            self.TRIGGER_CACHE_KEY,
            trigger_signal_flags,
            self.TRIGGER_SIGNAL_CACHE_TIMEOUT,
        )

    def process_latest_payout(self, instance: Multiplier) -> None:
        """
        Notify users when a signal is triggered.
        If the payout is below or equal to RESET_AT_TRIGGER, reset all flags.
        Otherwise, check thresholds and send notifications as needed.
        """
        payout = int(instance.crash)
        app = instance.worker.app

        # Reset all flags if the payout is below or equal to the reset threshold
        if payout <= self.RESET_AT_TRIGGER:
            self._batch_reset_trigger_flags()
            return

        trigger_signal_flags = self._get_trigger_signal_flags()

        for threshold in self.THRESHOLDS:
            has_been_triggered_before = trigger_signal_flags[app][threshold][
                "triggered"
            ]
            if payout >= threshold and not has_been_triggered_before:
                logger.info(
                    f"{app} {instance.worker.name} has triggered signal for {threshold}% chance."
                )
                # Update the trigger flag for this threshold
                trigger_signal_flags[app][threshold].update(
                    {
                        "triggered": True,
                        "triggered_at": instance.created_at,
                        "triggered_by": payout,
                    }
                )

                # Prepare notification details
                push_title = f"{instance.worker.app} Signal Alert"
                push_msg = (
                    f"{instance.worker.name} has reached your {threshold}% trigger. "
                    f"Tap to take action."
                )

                # Get subscribers for this app and threshold
                subscribers = get_app_threshold_subscribers(app, threshold)
                if subscribers:
                    # Send push notification to all subscribers
                    OneSignal.send_push(
                        type=NotificationChannel.PUSH.value,
                        title=push_title,
                        message=push_msg,
                        user_ids=list(subscribers),
                    )
                else:
                    logger.info(
                        f"No subscribers for {instance.worker.name} {app} at {threshold}%"
                    )

        # Save updated trigger flags to cache
        self._set_trigger_signal_flags(trigger_signal_flags)


# Singleton instance
SignalNotificationMonitor = SignalNotificationMonitor()
