from django.dispatch import receiver

from observers.models import Multiplier, post_bulk_create


@receiver(post_bulk_create, sender=Multiplier)
def handle_bulk_created(sender, instances, **kwargs):
    pass
