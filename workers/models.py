from django.db import models

from commons.constants import SeedName
from commons.models import Base
from commons.utils import generate_uuid


class Worker(Base):
    app = models.CharField(max_length=255, null=False, blank=False)
    name = models.CharField(max_length=255, choices=SeedName.choices())
    key = models.CharField(
        max_length=255, default=generate_uuid, unique=True, null=False
    )

    class Meta:
        unique_together = ("app", "name")
        ordering = ("-created_at",)

    def __str__(self):
        return self.name
