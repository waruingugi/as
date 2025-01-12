from django.db import models

from commons.constants import BettingApps
from commons.models import Base
from commons.utils import generate_uuid


class Worker(Base):
    app = models.CharField(
        max_length=255, choices=[(app, app.value) for app in BettingApps]
    )
    name = models.CharField(max_length=255, unique=True)
    key = models.CharField(
        max_length=255, default=generate_uuid, unique=True, null=False
    )

    def __str__(self):
        return self.name
