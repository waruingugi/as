import os
from collections import defaultdict

import requests
from django.core.cache import cache

from commons.constants import CacheKeys
from commons.logger import logger
from workers.models import Worker


def calculate_jaccard_similarity(set_1, set_2) -> float:
    """
    Calculate Jaccard similarity between two sets.
    """
    intersection = len(set_1 & set_2)
    union = len(set_1 | set_2)
    return intersection / union if union > 0 else 0


def find_similar_workers(worker_payouts, threshold=0.8) -> dict:
    """
    Compare workers for similarity based on Jaccard similarity.

    Args:
        worker_payouts (dict): Dictionary of worker IDs and their payout sets.
        threshold (float): Similarity threshold to consider workers as "similar".

    Returns:
        dict: Matched worker pairs and their similarity scores.
    """
    logger.info("Finding workers with similar payouts...")
    matched_workers = defaultdict(list)
    worker_ids = list(worker_payouts.keys())

    for i in range(len(worker_ids)):
        for j in range(i + 1, len(worker_ids)):
            worker_1 = worker_ids[i]
            worker_2 = worker_ids[j]

            # Calculate similarity
            similarity = calculate_jaccard_similarity(
                worker_payouts[worker_1], worker_payouts[worker_2]
            )
            if similarity >= threshold:
                matched_workers[(worker_1, worker_2)] = similarity

    return matched_workers


def reboot_worker(worker_id) -> None:
    """
    Reboot a worker pod by shutting it down in the Kubernetes cluster.
    """
    try:
        REBOOT_WORKERS = bool(int(os.environ["REBOOT_WORKERS"]))
        if REBOOT_WORKERS:  # Reboot workers only if setting is True
            worker = Worker.objects.get(id=worker_id)
            if cache.get(CacheKeys.REBOOTED_WORKER.format(worker_id)):
                logger.info(
                    f"Worker {worker.name} for {worker.app} was rebooted recently. Skipping..."
                )
                return

            logger.info(f"Rebooting {worker.name} for {worker.app}")

            # Parse the worker name and app
            seed_number = worker.name.split(" ")[-1][-1]  # Extract the seed number
            app_name = worker.app.lower()  # Convert app name to lowercase

            # Construct the pod name
            pod_name = f"{app_name}-seed-{seed_number}"

            # Fetch Kubernetes API base URL and token from environment variables
            kubernetes_base_url = os.getenv("KUBERNETES_API_BASE_URL")
            kubernetes_token = os.getenv("KUBERNETES_TOKEN")

            # Construct the request URL
            url = f"{kubernetes_base_url}/api/v1/namespaces/{app_name}/pods/{pod_name}"

            # Set up headers
            headers = {"Authorization": f"Bearer {kubernetes_token}"}

            # Send the DELETE request to shut down the pod
            response = requests.delete(url, headers=headers, verify=False)

            if response.status_code == 200:
                logger.info(f"Successfully rebooted worker pod: {pod_name}")
            else:
                logger.error(
                    f"Failed to reboot worker pod: {pod_name}. "
                    f"Status code: {response.status_code}, Response: {response.text}"
                )

    except Exception as e:
        logger.error(f"An error occurred while rebooting the worker: {str(e)}")
