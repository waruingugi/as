from django_filters import FilterSet, filters

from commons.constants import BettingApps
from workers.models import Worker


class WorkerFilter(FilterSet):
    # Filter for 'app' field using the BettingApps Enum
    app = filters.ChoiceFilter(choices=BettingApps.choices())

    class Meta:
        model = Worker
        fields = ["app"]
