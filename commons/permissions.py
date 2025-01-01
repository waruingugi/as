from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


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
