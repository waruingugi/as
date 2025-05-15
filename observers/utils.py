from django.core.cache import cache

from commons.constants import (
    DEFAULT_CACHE_DURATION,
    MULTIPLIER_PAGE_SIZE,
    CacheKeys,
)
from commons.logger import logger
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


class SignalNotificationMonitor:
    """
    Monitor for signal notifications.
    """

    SIGNAL_NOTIFICATION_TRIGGERS = (80, 85, 90, 95)
    RESET_AT_TRIGGER = 50

    def __init__(self) -> None:
        self.thresholds = self.SIGNAL_NOTIFICATION_TRIGGERS
        self.trigger_signal_flags = {}
        self.batch_reset_trigger_flags()

    def batch_reset_trigger_flags(self) -> None:
        for threshold in self.thresholds:
            self.trigger_signal_flags[threshold] = False

    def __call__(self, instances) -> None:
        # Pop most recent instance
        instance = instances[-1]
        payout = int(instance.payout)

        if payout <= self.RESET_AT_TRIGGER:
            self.batch_reset_trigger_flags()
            return

        elif payout in self.thresholds:
            if not self.trigger_signal_flags[payout]:
                self.trigger_signal_flags[payout] = True
                logger.info(f"Signal notification triggered for payout: {payout}x")
        else:
            pass
