from django.db import models

from commons.models import Base


class Multiplier(Base):
    crash = models.DecimalField(max_digits=10, decimal_places=2)
    worker = models.ForeignKey(
        "workers.Worker", on_delete=models.CASCADE, related_name="multipliers"
    )

    def __str__(self) -> str:
        return str(self.crash)
