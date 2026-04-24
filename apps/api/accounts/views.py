from datetime import timedelta
from typing import cast

from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .models import User
from .serializers import LoginSerializer, UserSerializer

_WS_TOKEN_TTL = timedelta(seconds=60)


def _issue_tokens(user) -> dict[str, str]:
    # for_user is typed on the parent Token class so mypy infers Token here;
    # RefreshToken is the actual runtime class (it declares the `access_token` property).
    refresh = cast(RefreshToken, RefreshToken.for_user(user))
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ws_token(request: Request) -> Response:
    """60-second signed token the rt-node gateway verifies on WS connect."""
    # IsAuthenticated guarantees request.user is our custom User model.
    user = cast(User, request.user)
    token = cast(AccessToken, AccessToken.for_user(user))
    token.set_exp(lifetime=_WS_TOKEN_TTL)
    token["tenant_id"] = user.tenant_id
    token["role"] = user.role
    token["scope"] = "ws"
    return Response(
        {"token": str(token), "expires_in": int(_WS_TOKEN_TTL.total_seconds())},
        status=status.HTTP_200_OK,
    )
