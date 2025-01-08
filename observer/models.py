from django.db import models

from commons.models import Base


class Multiplier(Base):
    crash = models.DecimalField(max_digits=10, decimal_places=2)
