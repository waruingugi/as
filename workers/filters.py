from django_filters import FilterSet, filters

from commons.constants import BettingApp
from workers.models import Worker


class WorkerFilter(FilterSet):
    # Filter for 'app' field using the BettingApp Enum
    app = filters.ChoiceFilter(choices=BettingApp.choices())

    class Meta:
        model = Worker
        fields = ["app"]
