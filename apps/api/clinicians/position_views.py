"""Clinician position endpoints.

- POST /api/v1/positions/ — a clinician reports their own GPS ping.
  Only role=clinician is allowed; the submitted row's tenant and
  clinician are both derived from the authenticated user so the client
  can't spoof them.
- GET /api/v1/positions/latest/ — schedulers/admins fetch the latest
  position for each clinician in the tenant, for the ops map.
"""

from django.db.models import Max
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsClinician, IsSchedulerOrAdmin

from .models import Clinician, ClinicianPosition
from .position_serializers import ClinicianPositionSerializer


class ClinicianPositionCreateView(generics.CreateAPIView):
    """POST own position; clinician+tenant derived from auth."""

    serializer_class = ClinicianPositionSerializer
    permission_classes = [IsAuthenticated, IsClinician]

    def perform_create(self, serializer) -> None:
        tenant = getattr(self.request, "tenant", None)
        if tenant is None:
            raise PermissionDenied("No tenant in context.")
        # IsClinician permission ensures user is authenticated; filter on its pk.
        user_id = self.request.user.pk
        clinician = Clinician.objects.filter(user_id=user_id, tenant=tenant).first()
        if clinician is None:
            raise PermissionDenied("Authenticated user is not a registered clinician.")
        serializer.save(tenant=tenant, clinician=clinician)


class ClinicianPositionLatestView(APIView):
    """GET latest position for every clinician in the current tenant."""

    permission_classes = [IsAuthenticated, IsSchedulerOrAdmin]

    def get(self, request: Request) -> Response:
        latest_ids = (
            ClinicianPosition.scoped.values("clinician_id")
            .annotate(max_ts=Max("ts"))
            .values_list("clinician_id", "max_ts")
        )
        rows = ClinicianPosition.scoped.filter(
            clinician_id__in=[cid for cid, _ in latest_ids]
        ).order_by("clinician_id", "-ts")

        # Reduce to one row per clinician (latest).
        by_clinician: dict[int, ClinicianPosition] = {}
        for row in rows:
            if row.clinician_id not in by_clinician:
                by_clinician[row.clinician_id] = row
        data = ClinicianPositionSerializer(list(by_clinician.values()), many=True).data
        return Response(data, status=status.HTTP_200_OK)
