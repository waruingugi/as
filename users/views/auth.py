from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.views import TokenObtainPairView

from users.serializers import UserTokenObtainPairSerializer


@extend_schema(tags=["auth"])
class UserTokenObtainPairView(TokenObtainPairView):
    serializer_class = UserTokenObtainPairSerializer
