from django.dispatch import receiver

from analytics.constants import CrashesToMonitor
from analytics.utils import cache_crash_intervals
from observers.models import Multiplier, post_bulk_create


@receiver(post_bulk_create, sender=Multiplier)
def new_crash_created(sender, instances, **kwargs):
    """Assert whether any instance in instances is greater than any element in CrashesToMonitor."""
    if any(
        float(instance.crash) >= crash
        for instance in instances
        for crash in CrashesToMonitor.list()
    ):
        cache_crash_intervals()
