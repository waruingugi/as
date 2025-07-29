import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

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


class WorkerHistoryConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.scope["user"] = await self.authenticate()
        except AuthenticationFailed:
            await self.close()
            return

        self.app = self.scope["url_route"]["kwargs"]["app"]
        if self.app not in BettingApp.list():
            await self.send_error(ErrorCodes.INVALID_APP_NAME.value)
            await self.close()
            return

        self.group_name = f"workerhistory_{self.app}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()
        await self.send_worker_history()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def history_update(self, event):
        await self.send_worker_history()

    async def send_worker_history(self):
        data = await self.get_crash_history(self.app)
        await self.send(text_data=json.dumps(data))

    @database_sync_to_async
    def get_crash_history(self, app):
        workers = Worker.objects.filter(app=app)
        if not workers.exists():
            raise NotFound(ErrorCodes.WORKERS_NOT_FOUND.value)

        history = get_workers_crash_history(app)
        serializer = WorkerHistorySerializer(history, many=True)
        return serializer.data

    @database_sync_to_async
    def authenticate(self):
        jwt_auth = JWTAuthentication()
        headers = dict(self.scope["headers"])
        if b"authorization" not in headers:
            raise AuthenticationFailed("No authorization header")
        auth_header = headers[b"authorization"].decode("utf-8")
        request = type("Request", (), {"META": {"HTTP_AUTHORIZATION": auth_header}})
        user_auth_tuple = jwt_auth.authenticate(request)
        if user_auth_tuple is None:
            raise AuthenticationFailed("Invalid token")
        return user_auth_tuple[0]

    async def send_error(self, message: str):
        await self.send(text_data=json.dumps({"error": message}))
