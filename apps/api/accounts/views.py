from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, UserSerializer


def _issue_tokens(user) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    refresh["tenant_id"] = user.tenant_id
    refresh["role"] = user.role
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request: Request) -> Response:
    ser = LoginSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = authenticate(
        request,
        username=ser.validated_data["email"],
        password=ser.validated_data["password"],
    )
    if user is None:
        return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    tokens = _issue_tokens(user)
    return Response({**tokens, "user": UserSerializer(user).data})
