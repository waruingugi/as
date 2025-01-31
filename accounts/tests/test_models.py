from uuid import uuid4

from django.test import TestCase
from django.utils.timezone import now, timedelta

from accounts.models import Subscription
from commons.constants import SubscriptionType, User


class SubscriptionModelTest(TestCase):
    def setUp(self) -> None:
        """Create a user but don't create a subscription automatically."""
        self.user = User.objects.create_user(
            phone_number="+254712345678", password=uuid4().hex, username="testuser1"
        )

    def test_create_subscription(self) -> None:
        """Ensure a subscription can be created successfully."""
        subscription = Subscription.objects.create(
            user=self.user,
            subscription_type=SubscriptionType.PRO,
            end_date=now() + timedelta(days=30),
        )

        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.subscription_type, SubscriptionType.PRO)
        self.assertTrue(subscription.is_active())

    def test_subscription_expires_correctly(self) -> None:
        """Check if subscription is_active status updates correctly."""
        expired_subscription = Subscription.objects.create(
            user=self.user,
            subscription_type=SubscriptionType.PRO,
            end_date=now() - timedelta(days=1),  # Expired yesterday
        )
        self.assertFalse(expired_subscription.is_active())
        expired_subscription.delete()

        active_subscription = Subscription.objects.create(
            user=self.user,
            subscription_type=SubscriptionType.PRO,
            end_date=now() + timedelta(days=5),  # Still valid
        )
        self.assertTrue(active_subscription.is_active())

    def test_subscription_renewal(self) -> None:
        """Ensure renewing a subscription extends the expiration date."""
        subscription = Subscription.objects.create(
            user=self.user,
            subscription_type=SubscriptionType.PRO,
            end_date=now() + timedelta(days=30),
        )

        original_end_date = subscription.end_date
        subscription.renew(months=2)  # Extend by 2 months

        self.assertGreater(subscription.end_date, original_end_date)
        self.assertEqual(subscription.end_date, original_end_date + timedelta(days=60))

    def test_user_has_no_subscription_by_default(self) -> None:
        """A user without a subscription should return false for has_active_subscription."""
        self.assertFalse(self.user.has_active_subscription)
        self.assertEqual(self.user.subscription_type, "none")

    def test_user_has_active_subscription(self) -> None:
        """A user with an active subscription should return true for has_active_subscription."""
        Subscription.objects.create(
            user=self.user,
            subscription_type=SubscriptionType.PRO,
            end_date=now() + timedelta(days=30),
        )

        self.assertTrue(self.user.has_active_subscription)
        self.assertEqual(self.user.subscription_type, SubscriptionType.PRO)

    def test_user_subscription_expires(self) -> None:
        """Ensure has_active_subscription updates correctly when a subscription expires."""
        subscription = Subscription.objects.create(
            user=self.user,
            subscription_type=SubscriptionType.PRO,
            end_date=now() + timedelta(days=1),
        )

        self.assertTrue(self.user.has_active_subscription)

        # Simulate expiration
        subscription.end_date = now() - timedelta(days=1)
        subscription.save()

        self.assertFalse(self.user.has_active_subscription)
