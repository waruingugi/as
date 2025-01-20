# views.py
import os

from rest_framework.response import Response
from rest_framework.views import APIView

from commons.permissions import IsWorkerPermission


class WorkerCredentialsView(APIView):
    """
    Returns the phone number and password for the worker making the request.
    A valid API-KEY must be provided in the headers.
    """

    permission_classes = [IsWorkerPermission]

    def get(self, request, *args, **kwargs):
        # TODO: Some validation here to determine which credentials to send back
        data = {
            "phone_number": os.environ["PHONE_NUMBER"],
            "password": os.environ["PASSWORD"],
        }
        return Response(data)
