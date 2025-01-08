from django.db import models

from commons.models import Base


class Multiplier(Base):
    cash_out = models.DecimalField(max_digits=10, decimal_places=2)
