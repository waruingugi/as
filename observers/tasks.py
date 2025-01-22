import random
from collections import defaultdict

from celery import shared_task

from commons.constants import BettingApps
from commons.logger import logger
from observers.models import Multiplier
from observers.utils import find_similar_workers, reboot_worker
from workers.models import Worker


@shared_task
def identify_similar_workers(threshold=0.8) -> None:
    """
    Find workers posting similar payouts and reboot one randomly if necessary.
    """
    for app in BettingApps.list():
        logger.info("Starting task to identify similar workers...")
        # Get workers for the current app
        workers = Worker.objects.filter(app=app).values_list("id", flat=True)

        # Organize multipliers into a dictionary of sets
        worker_payouts = defaultdict(set)
        for worker in workers:
            recent_payouts = (
                Multiplier.objects.filter(worker_id=worker)
                .order_by("-created_at")
                .values_list("crash", flat=True)[:10]
            )
            worker_payouts[worker].update(recent_payouts)

        # Find similar workers
        matched_workers = find_similar_workers(worker_payouts, threshold)

        # Handle matched workers
        handled_workers = (
            set()
        )  # To avoid rebooting multiple workers from the same group

        for pair, similarity in matched_workers.items():
            worker_1, worker_2 = pair

            # Randomly choose one worker to reboot
            if worker_1 not in handled_workers and worker_2 not in handled_workers:
                logger.info(f"Randomly choosing  {app} worker to reboot.")
                chosen_worker = random.choice([worker_1, worker_2])
                reboot_worker(chosen_worker)

                # Mark the workers as handled
                handled_workers.add(worker_1)
                handled_workers.add(worker_2)
