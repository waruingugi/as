from django.db.models.signals import post_save
from django.dispatch import receiver

from commons.utils import UserSignalSettingsCacheManager
from users.models import SignalSetting


@receiver(post_save, sender=SignalSetting)
def update_users_signal_prefs(sender, instance, **kwargs):
    """
    Update the users_signal_prefs cache when an action is performed on an instance's preference.
    """
    if instance.preference:
        UserSignalSettingsCacheManager.update(instance)
