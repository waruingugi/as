from rest_framework.generics import CreateAPIView

from workers.models import Worker
from workers.serializers import WorkerCreateSerializer


class WorkerCreateView(CreateAPIView):
    queryset = Worker.objects.all()
    serializer_class = WorkerCreateSerializer
