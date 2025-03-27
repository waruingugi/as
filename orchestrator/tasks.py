import random
from collections import defaultdict

from celery import shared_task
from django.utils.timezone import now, timedelta

from commons.constants import BettingApp
from commons.logger import logger
from observers.models import Multiplier
from orchestrator.utils import find_similar_workers, reboot_worker
from workers.models import Worker


@shared_task
def identify_similar_workers(threshold=0.8) -> None:
    """
    Find workers posting similar payouts and reboot one randomly if necessary.
    """
    for app in BettingApp.list():
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
        handled_workers = set()

        for pair, _ in matched_workers.items():
            worker_1, worker_2 = pair

            # Randomly choose one worker to reboot
            if worker_1 not in handled_workers and worker_2 not in handled_workers:
                logger.info(f"Randomly choosing a {app} worker to reboot.")
                chosen_worker = random.choice([worker_1, worker_2])

                # Reboot the worker if not recently rebooted
                reboot_worker(chosen_worker)

                # Mark the workers as handled
                handled_workers.add(worker_1)
                handled_workers.add(worker_2)


@shared_task
def find_failing_workers():
    """
    Check if any worker is stale (worker is not posting payouts) for 5 minutes,
    and reboot the worker if necessary.
    """
    logger.info("Starting task to check for failed workers...")
    try:
        # Get the current time and the 5-minute threshold
        five_minutes_ago = now() - timedelta(minutes=5)

        # Fetch all workers
        workers = Worker.objects.all()

        for worker in workers:
            # Check the most recent crash time for this worker
            recent_crash = (
                Multiplier.objects.filter(worker=worker)
                .order_by("-created_at")
                .values_list("created_at", flat=True)
                .first()
            )

            if not recent_crash or recent_crash < five_minutes_ago:
                # Worker has not posted any crash in the last 5 minutes
                logger.info(
                    f"Worker {worker.app}-{worker.name} has been inactive since {recent_crash}. Rebooting..."
                )
                reboot_worker(worker.id)

    except Exception as e:
        logger.error(f"Error: {str(e)}")


# @shared_task
# def find_failing_workers():
#     """
#     Check if any worker is stale (worker is not posting payouts) for 5 minutes,
#     and reboot the worker if necessary.
#     """
#     logger.info("Starting task to find failed workers...")
#
#     CPU_THRESHOLD = 0.6  # Any worker with CPU usage below 0.5 cores will be rebooted
#
#     # Disable SSL warnings
#     urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#
#     metrics_url = f"{KUBERNETES_API_BASE_URL}/apis/metrics.k8s.io/v1beta1/pods/"
#     headers = {
#         "Authorization": f"Bearer {KUBERNETES_TOKEN}",
#     }
#     response = requests.get(metrics_url, headers=headers, verify=False)
#
#     if response.status_code == status.HTTP_200_OK:
#         pods = response.json().get("items", [])
#         valid_namespaces = [app.lower() for app in BettingApp.list()]
#
#         for pod in pods:
#             pod_name = pod.get("metadata", {}).get("name", "")
#             namespace = pod.get("metadata", {}).get("namespace", "")
#             cpu_usage = pod.get("containers", [])[0].get("usage", {}).get("cpu", "")
#
#             if namespace in valid_namespaces:
#                 if cpu_usage and float(cpu_usage.rstrip("n")) < CPU_THRESHOLD * 1e9:  # Convert 0.5 to nanocores
#                     logger.info(f"Pod {pod_name} CPU usage is below {CPU_THRESHOLD} cores. Taking action...")
#
#                     # Extract seed number from pod name
#                     seed_number = pod_name.split("-")[-1]
#                     app_name = namespace.upper()
#
#                     # Find the corresponding worker
#                     worker_name = f"Seed {seed_number.zfill(2)}"
#                     try:
#                         worker = Worker.objects.get(name=worker_name, app=app_name)
#                         reboot_worker(worker.id)
#                     except Worker.DoesNotExist:
#                         logger.error(f"No worker found for pod {pod_name} with name {worker_name} and app {app_name}")
#
#     else:
#         logger.error(f"Failed to fetch pod metrics. Status code: {response.status_code}, Response: {response.text}")
