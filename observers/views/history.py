from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from commons.constants import BettingApp
from commons.errors import ErrorCodes
from observers.serializers import WorkerHistorySerializer
from observers.utils import get_workers_crash_history
from workers.models import Worker


class WorkerHistoryView(APIView):
    """
    Returns the last `count` multipliers (payouts) for each Worker
    belonging to a specific app.
    """

    serializer_class = WorkerHistorySerializer

    def get(self, request, app):
        # Validate app_name
        if app not in BettingApp.list():
            return Response(
                {"error": ErrorCodes.INVALID_APP_NAME.value},
                status=status.HTTP_400_BAD_REQUEST,
            )
        workers = Worker.objects.filter(app=app)
        if not workers.exists():
            raise NotFound(ErrorCodes.WORKERS_NOT_FOUND.value)

        crash_history = get_workers_crash_history(app)

        serializer = WorkerHistorySerializer(crash_history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
