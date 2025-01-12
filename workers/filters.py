from django_filters import FilterSet, filters

from commons.constants import BettingApps
from workers.models import Worker


class WorkerFilter(FilterSet):
    # Filter for 'app' field using the BettingApps Enum
    app = filters.ChoiceFilter(choices=[(app.value, app.value) for app in BettingApps])

    class Meta:
        model = Worker
        fields = ["app"]
