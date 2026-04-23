from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    tenant = getattr(request, "tenant", None)
    return Response({"ok": True, "tenant": tenant.name if tenant else None})
