from uuid import uuid4

from django.db import models

from commons.constants import BettingApps
from commons.models import Base


class Worker(Base):
    app = models.CharField(
        max_length=255, choices=[(app, app.value) for app in BettingApps]
    )
    name = models.CharField(max_length=255, unique=True)
    key = models.CharField(
        max_length=255, default=lambda: uuid4().hex, unique=True, null=False
    )

    def __str__(self):
        return self.name
