import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

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


# consumers.py


class ProbabilityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Authenticate JWT from query string
        try:
            self.scope["user"] = await self.authenticate()
        except AuthenticationFailed:
            await self.close()
            return

        self.app = self.scope["url_route"]["kwargs"]["app"]

        if self.app not in BettingApp.list():
            await self.close()
            return

        self.group_name = f"probabilities_{self.app}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send initial data
        await self.send_probabilities()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_probabilities(self):
        data = await self.get_worker_probabilities(self.app)
        await self.send(text_data=json.dumps(data))

    async def probability_update(self, event):
        await self.send_probabilities()

    @database_sync_to_async
    def get_worker_probabilities(self, app):
        workers = Worker.objects.filter(app=app)
        if not workers.exists():
            return {"error": "No workers found"}

        response_data = [format_worker_probabilities(w) for w in workers]
        serializer = WorkerProbabilitySerializer(response_data, many=True)
        return serializer.data

    @database_sync_to_async
    def authenticate(self):
        jwt_auth = JWTAuthentication()
        headers = dict(self.scope["headers"])
        if b"authorization" not in headers:
            raise AuthenticationFailed("No authorization header")
        auth_header = headers[b"authorization"].decode("utf-8")
        # Prepare the header as expected by JWTAuthentication.authenticate
        request = type("Request", (), {"META": {"HTTP_AUTHORIZATION": auth_header}})
        user_auth_tuple = jwt_auth.authenticate(request)
        if user_auth_tuple is None:
            raise AuthenticationFailed("Invalid token")
        return user_auth_tuple[0]
