from django.db import models
from django.dispatch import Signal

from commons.models import Base

post_bulk_create = Signal()


class MultiplierManager(models.Manager):
    def bulk_create(self, objs, **kwargs):
        created_objects = super().bulk_create(objs, **kwargs)
        # Trigger custom bulk_created signal
        post_bulk_create.send(sender=self.model, instances=created_objects)

        return created_objects


class Multiplier(Base):
    crash = models.DecimalField(max_digits=10, decimal_places=2)
    worker = models.ForeignKey(
        "workers.Worker", on_delete=models.CASCADE, related_name="multipliers"
    )

    class Meta:
        indexes = [
            models.Index(fields=["worker", "crash", "created_at"]),
        ]
        ordering = ["-created_at"]

    objects = MultiplierManager()

    def __str__(self) -> str:
        return str(self.crash)
