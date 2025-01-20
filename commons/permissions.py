from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from commons.errors import ErrorCodes
from workers.models import Worker


class IsWorkerPermission(BasePermission):
    """
    Custom permission to only allow workers to make permissions
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        api_key = request.headers.get("API-KEY")
        if not api_key:
            raise AuthenticationFailed(ErrorCodes.WORKER_API_KEY_IS_REQUIRED.value)
        try:
            worker = Worker.objects.get(key=api_key)
        except Worker.DoesNotExist:
            raise AuthenticationFailed(ErrorCodes.INVALID_WORKER_API_KEY.value)

        view.worker = worker
        return True


class IsStaffPermission(BasePermission):
    """
    Custom permission to only allow staff API keys to make requests.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.user.is_staff  # type: ignore


class IsStaffOrSelfPermission(BasePermission):
    """
    Custom permission to only allow staff or the user itself to view and edit their data.
    """

    def has_object_permission(self, request, view, obj):
        # Check if the user is staff or if the user is the object's owner
        return (
            request.user.is_staff
            or obj == request.user
            or (hasattr(obj, "user") and obj.user == request.user)
        )
