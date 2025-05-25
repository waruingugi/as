import json

from django.core.cache import cache

from analytics.services import Probability
from commons.constants import (
    DEFAULT_CACHE_DURATION,
    MULTIPLIER_PAGE_SIZE,
    RESET_SIGNALS_AT_TRIGGER,
    SIGNAL_NOTIFICATION_TRIGGERS,
    BettingApp,
    CacheKeys,
    SeedName,
)
from commons.logger import logger
from commons.tasks import send_push_task
from notifications.constants import (
    NotificationChannel,
)
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


# class SignalNotificationMonitor:
#     """
#     Monitor for signal notifications.
#     """
#
#     RESET_AT_TRIGGER = 50
#     TRIGGER_SIGNAL_CACHE_TIMEOUT = None  # Cache never expires
#     TRIGGER_CACHE_KEY = CacheKeys.TRIGGER_SIGNAL_FLAGS
#     THRESHOLDS = SIGNAL_NOTIFICATION_TRIGGERS
#
#     def _reset_seed_trigger_flags(self, app: str, seed: str) -> None:
#         """
#         Reset all trigger signal flags for a specific app and seed.
#         """
#         trigger_signal_flags = self._get_trigger_signal_flags()
#         if app in trigger_signal_flags and seed in trigger_signal_flags[app]:
#             for threshold in self.THRESHOLDS:
#                 trigger_signal_flags[app][seed][threshold].update(
#                     {
#                         "triggered": False,
#                         "triggered_at": None,
#                         "triggered_by": None,
#                     }
#                 )
#             self._set_trigger_signal_flags(trigger_signal_flags)
#
#     def _batch_reset_trigger_flags(self) -> None:
#         """
#         Reset all trigger signal flags for all apps and thresholds.
#         """
#         trigger_signal_flags = {
#             app: {
#                 seed: {
#                     threshold: {
#                         "triggered": False,
#                         "triggered_at": None,
#                         "triggered_by": None,
#                     }
#                     for threshold in self.THRESHOLDS
#                 }
#                 for seed in SeedName.list()
#             }
#             for app in BettingApp.list()
#         }
#         self._set_trigger_signal_flags(trigger_signal_flags)
#
#     def _get_trigger_signal_flags(self) -> dict:
#         """
#         Get the current signal trigger flags from cache.
#         If not present, initialize them.
#         """
#         cached = cache.get(self.TRIGGER_CACHE_KEY, {})
#         if not cached:
#             self._batch_reset_trigger_flags()
#             cached = cache.get(self.TRIGGER_CACHE_KEY)  # Fetch again after initialization
#         return cached
#
#     def _set_trigger_signal_flags(self, trigger_signal_flags: dict) -> None:
#         """
#         Set the current signal trigger flags in cache.
#         """
#         cache.set(
#             self.TRIGGER_CACHE_KEY,
#             dict(trigger_signal_flags),  # Convert default dict to regular dict for caching
#             self.TRIGGER_SIGNAL_CACHE_TIMEOUT,
#         )
#
#     def process_latest_payout(self, instance: Multiplier) -> None:
#         """
#         Notify users when a signal is triggered.
#         If the payout is below or equal to RESET_AT_TRIGGER, reset all flags.
#         Otherwise, check thresholds and send notifications as needed.
#         """
#         payout = int(instance.crash)
#         app = instance.worker.app
#         seed = instance.worker.name
#
#         # Reset all flags if the payout is below or equal to the reset threshold
#         if payout <= self.RESET_AT_TRIGGER:
#             self._reset_seed_trigger_flags(app, seed)
#             return
#
#         trigger_signal_flags = self._get_trigger_signal_flags()
#
#         for threshold in self.THRESHOLDS:
#             has_been_triggered_before = trigger_signal_flags[app][seed][threshold][
#                 "triggered"
#             ]
#             if payout >= threshold and not has_been_triggered_before:
#                 logger.info(
#                     f"{app} {instance.worker.name} has triggered signal for {threshold}% chance."
#                 )
#                 # Update the trigger flag for this threshold
#                 trigger_signal_flags[app][seed][threshold].update(
#                     {
#                         "triggered": True,
#                         "triggered_at": instance.created_at,
#                         "triggered_by": payout,
#                     }
#                 )
#
#                 # Prepare notification details
#                 push_title = f"{instance.worker.app} Signal Alert"
#                 push_msg = (
#                     f"{instance.worker.name} has reached your {threshold}% trigger. "
#                     f"Tap to take action."
#                 )
#
#                 # Get subscribers for this app and threshold
#                 subscribers = get_app_threshold_subscribers(app, threshold)
#                 if subscribers:
#                     # Send push notification to all subscribers
#                     OneSignal.send_push(
#                         type=NotificationChannel.PUSH.value,
#                         title=push_title,
#                         message=push_msg,
#                         user_ids=list(subscribers),
#                     )
#                 else:
#                     logger.info(
#                         f"No subscribers for {instance.worker.name} {app} at {threshold}%"
#                     )
#
#         # Save updated trigger flags to cache
#         self._set_trigger_signal_flags(trigger_signal_flags)
#
#
# # Singleton instance
# SignalNotificationMonitor = SignalNotificationMonitor()


class SignalNotificationMonitor:
    """
    Monitor for signal notifications using Django cache locks to avoid race conditions.

    Responsibilities:
      - Determine when to reset flags (_should_reset)
      - Generate unique cache keys (_flag_key)
      - Atomically mark first triggers (_mark_first_trigger)
      - Reset flags for a seed or all seeds (_reset_seed_flags, batch_reset_all)
      - Create and dispatch notifications (_send_notification)

    Uses `cache.set(..., nx=True)` for atomic writes and a distributed lock
    to serialize reset operations across workers.
    """

    RESET_AT_TRIGGER = RESET_SIGNALS_AT_TRIGGER
    THRESHOLDS = SIGNAL_NOTIFICATION_TRIGGERS
    BASE_KEY = CacheKeys.TRIGGER_SIGNAL_FLAGS
    CACHE_TIMEOUT = None  # never expire
    LOCK_KEY = f"{BASE_KEY}:lock"
    LOCK_TIMEOUT = 5  # seconds

    @classmethod
    def process_latest_payout(cls, instance: Multiplier) -> None:
        app = instance.worker.app
        seed = instance.worker.name
        payout = int(instance.crash)
        probability = Probability.calculate_probability(
            worker_id=str(instance.worker.id), crash=payout
        )

        # Acquire lock only for flag operations (fast cache ops)
        lock = cache.lock(cls.LOCK_KEY, timeout=cls.LOCK_TIMEOUT)
        triggered = []
        with lock:
            if cls._should_reset(probability):
                cls._reset_seed_flags(app, seed)
            else:
                for threshold in cls.THRESHOLDS:
                    if probability >= threshold:
                        if cls._mark_first_trigger(app, seed, threshold, instance):
                            triggered.append((app, seed, threshold, instance))

        # Outside lock: send notifications for newly triggered thresholds
        for app, seed, threshold, inst in triggered:
            cls._send_notification(app, seed, threshold, inst)

    @classmethod
    def _should_reset(cls, probability: float) -> bool:
        """Return True if the probability is at or below the reset threshold."""
        return probability <= cls.RESET_AT_TRIGGER

    @classmethod
    def _flag_key(cls, app: str, seed: str, threshold: int) -> str:
        """Create a unique cache key for an (app, seed, threshold) combo."""
        return f"{cls.BASE_KEY}:{app}:{seed}:{threshold}"

    @classmethod
    def _mark_first_trigger(
        cls, app: str, seed: str, threshold: int, instance: Multiplier
    ) -> bool:
        """
        Atomically record the first crossing using cache.set(nx=True).
        Returns True only if this is the first time the key was set.
        """
        key = cls._flag_key(app, seed, threshold)
        payload = json.dumps(
            {
                "triggered_at": instance.created_at.isoformat(),
                "triggered_by": float(instance.crash),
            }
        )
        return cache.set(key, payload, timeout=cls.CACHE_TIMEOUT, nx=True)

    @classmethod
    def _reset_seed_flags(cls, app: str, seed: str) -> None:
        """Clear flags for a specific app and seed by deleting each key."""
        for threshold in cls.THRESHOLDS:
            cache.delete(cls._flag_key(app, seed, threshold))

    @classmethod
    def batch_reset_all(cls) -> None:
        """
        Reset flags for every app and seed across all thresholds.
        """
        lock = cache.lock(cls.LOCK_KEY, timeout=cls.LOCK_TIMEOUT)
        with lock:
            for app in BettingApp.list():
                for seed in SeedName.list():
                    cls._reset_seed_flags(app, seed)

    @classmethod
    def _send_notification(
        cls, app: str, seed: str, threshold: int, instance: Multiplier
    ) -> None:
        """Build and dispatch a push notification for a threshold crossing."""
        title = f"{app} Signal Alert"
        message = f"{seed} has reached your {threshold}% trigger. Tap to take action."
        logger.info(f"Notifying {app} {seed} subscribers for {threshold}% trigger")

        subscribers = get_app_threshold_subscribers(app, threshold)
        if not subscribers:
            logger.info(f"No subscribers for {seed} {app} at {threshold}%")
            return
        try:
            # schedule background task
            send_push_task.delay(
                type=NotificationChannel.PUSH.value,
                title=title,
                message=message,
                user_ids=list(subscribers),
            )
        except Exception as e:
            logger.error(
                f"Failed to enqueue push for {app}:{seed}:{threshold} trigger -> {e}"
            )
