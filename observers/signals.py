from django.dispatch import receiver

from observers.models import Multiplier, post_bulk_create
from observers.tasks import (
    broadcast_history_task,
    broadcast_probability_task,
    broadcast_strategies_task,
    execute_signal_engine_task,
    trigger_computations_task,
)


@receiver(post_bulk_create, sender=Multiplier)
def handle_bulk_created(sender, instances, **kwargs) -> None:
    """
    Signal to handle bulk-created Multiplier instances.
    Delegates analytics-related tasks (e.g., cache updates) to the analytics app.
    """
    if not instances:
        return

    # Trigger background computations
    instance_ids = [instance.id for instance in instances]
    trigger_computations_task.delay(instance_ids)

    # Broadcast probabilities and history updates
    broadcast_probability_task.delay(
        instances[-1].worker.app
    )  # Assuming the last instance's worker app is the target

    broadcast_history_task.delay(instances[-1].worker.app)

    broadcast_strategies_task.delay(instances[-1].worker.app)

    # Execute the signal engine task
    execute_signal_engine_task.delay(instances[-1].id)
