from django.db import models
from django.utils.timezone import now, timedelta

from commons.constants import SubscriptionType, User


class Subscription(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="subscription"
    )
    subscription_type = models.CharField(
        max_length=10,
        choices=SubscriptionType.choices(),
        default=SubscriptionType.PRO,
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()

    def is_active(self) -> bool:
        """Check if subscription is still valid."""
        return self.end_date > now()

    def renew(self, months: int = 1):
        """Renew subscription by extending the end date."""
        self.end_date = max(self.end_date, now()) + timedelta(days=30 * months)
        self.save()

    def __str__(self) -> str:
        return f"{self.user.phone_number} - {self.subscription_type} (Expires: {self.end_date})"
