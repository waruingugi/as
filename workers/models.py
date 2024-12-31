from django.db import models

from commons.constants import BettingApps
from commons.models import Base


class Workers(Base):
    app = models.CharField(max_length=255, null=False)
    name = models.CharField(
        max_length=255, choices=[(app, app.value) for app in BettingApps]
    )
    key = models.CharField(max_length=255, null=False)

    def __str__(self):
        return self.name
