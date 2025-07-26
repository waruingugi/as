import json

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.serializers import WorkerProbabilitySerializer
from analytics.utils import format_worker_probabilities
from commons.constants import BettingApp
from commons.errors import ErrorCodes
from workers.models import Worker


class WorkerProbabilitiesView(APIView):
    serializer_class = WorkerProbabilitySerializer

    def get(self, request, app):
        if app not in BettingApp.list():
            return Response(
                {"error": ErrorCodes.INVALID_APP_NAME.value},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workers = Worker.objects.filter(app=app)
        if not workers.exists():
            raise NotFound(ErrorCodes.WORKERS_NOT_FOUND.value)

        # Prepare the response data
        response_data = [format_worker_probabilities(worker) for worker in workers]
        serializer = WorkerProbabilitySerializer(response_data, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkerProbabilitiesStreamView(APIView):
    serializer_class = WorkerProbabilitySerializer

    def get(self, request, app):
        if app not in BettingApp.list():
            return Response(
                {"error": ErrorCodes.INVALID_APP_NAME.value},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workers = Worker.objects.filter(app=app)
        if not workers.exists():
            raise NotFound(ErrorCodes.WORKERS_NOT_FOUND.value)

        def stream():
            # Start the JSON array
            yield "["
            first = True
            # Iterate over workers using an iterator for memory efficiency
            for worker in workers.iterator():
                # Format the worker's probability data
                data = format_worker_probabilities(worker)
                # Serialize the data
                serialized = WorkerProbabilitySerializer(data).data
                # Add a comma before each item except the first
                if not first:
                    yield ","
                else:
                    first = False

                # Yield the serialized data as a JSON string
                yield json.dumps(serialized)
            # End the JSON array
            yield "]"

        return StreamingHttpResponse(
            stream(), content_type="application/json", status=status.HTTP_200_OK
        )
