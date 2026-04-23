from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from tenancy.managers import clear_current_tenant, set_current_tenant
from tenancy.models import Tenant

_BEARER_PREFIX = "Bearer "
_REQUEST_TENANT_KEY = "tenant"


def _raw_token_from_request(request: HttpRequest) -> bytes | None:
    """Return the raw JWT bytes from the Authorization header, or None.

    JWTAuthentication.get_header / get_raw_token expect a DRF Request, not a
    plain HttpRequest, so we pull the header ourselves and let the auth class
    handle validation.
    """
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.startswith(_BEARER_PREFIX):
        return None
    return header[len(_BEARER_PREFIX) :].encode()


def _attach_tenant(request: HttpRequest, tenant: Tenant | None) -> None:
    """Stash the tenant on the request in a way that's honest about its dynamism.

    HttpRequest stubs don't declare a `tenant` attribute (it's an ad-hoc addition
    for this project), so we write it via __dict__ to avoid either a mypy
    complaint or a ruff B010 (setattr-with-constant) warning.
    """
    request.__dict__[_REQUEST_TENANT_KEY] = tenant


class TenantMiddleware:
    """Attach the caller's Tenant to every request based on the JWT `tenant_id` claim.

    Also pushes the tenant into a contextvar so TenantScopedManager instances
    automatically filter by it. Anonymous requests get `request.tenant = None`
    and no contextvar is set (scoped managers return empty).
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        _attach_tenant(request, None)
        raw = _raw_token_from_request(request)
        if raw is not None:
            try:
                token = self.jwt_auth.get_validated_token(raw)
                tenant_id = token.get("tenant_id")
                if tenant_id:
                    tenant_obj = Tenant.objects.filter(id=tenant_id).first()
                    _attach_tenant(request, tenant_obj)
                    if tenant_obj is not None:
                        set_current_tenant(tenant_obj)
            except InvalidToken:
                pass
        try:
            return self.get_response(request)
        finally:
            clear_current_tenant()
