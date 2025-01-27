from django.core.cache import cache

from commons.constants import DEFAULT_CACHE_DURATION, CacheKeys
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


def get_worker_crash_list(worker_id: str, count: int) -> list:
    """
    Fetch the last `count` crashes for a worker from the database.
    """
    multipliers_qs = Multiplier.objects.filter(worker_id=worker_id).order_by(
        "-created_at"
    )[:count]
    return [
        {
            "created_at": m.created_at,
            "crash": m.crash,
        }
        for m in multipliers_qs
    ]


def get_workers_crash_history(
    app: str, count: int = 50, recompute: bool = False
) -> list:
    workers = Worker.objects.filter(app=app)
    if not workers.exists():  # Handle empty queryset
        return []

    data = []
    for worker in workers:
        cache_key = CacheKeys.WORKER_CRASH_QUERY.format(worker.id)

        if recompute:
            crash_list = get_worker_crash_list(worker.id, count)  # type: ignore
            cache.set(cache_key, crash_list, DEFAULT_CACHE_DURATION)
        else:
            crash_list = cache.get(cache_key)
            if crash_list is None:
                crash_list = get_worker_crash_list(worker.id, count)  # type: ignore
                cache.set(cache_key, crash_list, DEFAULT_CACHE_DURATION)

        data.append({"id": worker.id, "name": worker.name, "crash": crash_list})

    return data
