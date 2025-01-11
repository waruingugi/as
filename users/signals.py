from django.db.models.signals import post_save
from django.dispatch import receiver

from users.models import User
from users.utils import username_generator


@receiver(post_save, sender=User)
def set_username(sender, instance, created, **kwargs):
    if created and not instance.username:
        instance.username = username_generator()
        instance.save()
