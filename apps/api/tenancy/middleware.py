from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from tenancy.models import Tenant


class TenantMiddleware:
    """Attach the caller's Tenant to every request based on the JWT `tenant_id` claim.

    Anonymous requests get `request.tenant = None`.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.tenant = None  # type: ignore[attr-defined]
        header = self.jwt_auth.get_header(request)
        if header is not None:
            try:
                raw = self.jwt_auth.get_raw_token(header)
                if raw is not None:
                    token = self.jwt_auth.get_validated_token(raw)
                    tenant_id = token.get("tenant_id")
                    if tenant_id:
                        request.tenant = Tenant.objects.filter(id=tenant_id).first()  # type: ignore[attr-defined]
            except InvalidToken:
                pass
        return self.get_response(request)
