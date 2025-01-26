from analytics.services.probability import Probability
from commons.logger import logger
from workers.models import Worker


def purge_all_caches():
    """Purge crash intervals and query caches for all workers."""
    try:
        # Fetch all worker IDs
        worker_ids = Worker.objects.values_list("id", flat=True)

        # Purge caches for each worker
        for worker_id in worker_ids:
            Probability.purge_crash_intervals_cache_for_worker(worker_id)
            Probability.purge_crash_query_cache_for_worker(worker_id)

        logger.info(
            "Successfully purged all cache intervals and queries for all workers."
        )
    except Exception as e:
        logger.error(f"Error purging caches for all workers: {e}")
