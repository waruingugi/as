# Create your views here.
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView


class AppVersionView(APIView):
    """
    Returns the current app version from settings.
    """

    permission_classes = []  # No permission required
    serializer_class = None

    def get(self, request):
        app_version = settings.APP_VERSION
        return Response({"app_version": app_version})
