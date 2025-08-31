from django.core.cache import cache

from commons.constants import (
    DEFAULT_CACHE_DURATION,
    MULTIPLIER_PAGE_SIZE,
    CacheKeys,
)
from commons.logger import logger
from commons.utils import get_room_name
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

        data.append(
            {
                "id": worker.id,
                "name": worker.name,
                "room_name": get_room_name(worker.app, worker.name),
                "crash": crash_list,
            }
        )

    return data


def get_app_subscribers(app: str) -> set:
    """
    Get the subscribers for a specific app.
    """
    cache_key = cache.get(CacheKeys.USERS_SIGNAL_SETTINGS, {})
    subscribers = cache_key.get(app, set())
    return subscribers


def set_room_name(*, app: str, worker_name: str, room_no: int | None = None) -> None:
    """
    k8 Pods periodically restart, which means their rooms may change.
    This function links the room name to the seed name.
    Example: SEED 01 -> Room 01
    If room_no is None, it will use the worker_name to derive the room name.
    """
    if room_no is None:
        room_name = worker_name
        room_name = room_name.replace("Seed", "Room")
    else:
        room_name = f"Room 0{room_no}"

    cache_key = CacheKeys.SEED_TO_ROOM_MAPPING.format(app, worker_name)
    cache.set(cache_key, room_name, DEFAULT_CACHE_DURATION)


def get_strategy_data(app: str) -> list[dict]:
    """Fetch the latest strategy data for a given app from cache."""
    workers = Worker.objects.filter(app=app)
    strategy_data = []
    for worker in workers:
        cache_key = CacheKeys.SIGNAL_RECORD.format(worker.id)
        data = cache.get(cache_key, {})
        worker_data = {
            "id": worker.id,
            "name": worker.name,
            "room_name": get_room_name(worker.app, worker.name),
            "data": data,
        }
        strategy_data.append(worker_data)

    return strategy_data
