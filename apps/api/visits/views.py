from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from clinicians.models import Clinician
from core.permissions import IsSchedulerOrAdmin
from core.viewsets import BaseTenantViewSet

from .models import Visit
from .serializers import VisitSerializer
from .services import ConflictError, assign, cancel, check_in, check_out

# Actions a clinician can fire on their own assigned visits.
_CLINICIAN_ACTIONS = {"list", "retrieve", "check_in", "check_out"}


class VisitViewSet(BaseTenantViewSet):
    """Full CRUD plus the visit state-machine actions.

    Permission shape:
    - assign / cancel / create / update / destroy → scheduler/admin only.
    - list / retrieve / check-in / check-out → any authenticated tenant
      member (clinicians can see + transition their own day's visits).
      Tenant scoping is handled by Visit.scoped; per-visit ownership is
      enforced inside the state-machine for transitions.
    """

    serializer_class = VisitSerializer

    def get_permissions(self):
        if self.action in _CLINICIAN_ACTIONS:
            return [IsAuthenticated()]
        return [IsSchedulerOrAdmin()]

    def get_queryset(self):
        return Visit.scoped.all()

    @action(detail=True, methods=["post"])
    def assign(self, request: Request, pk: str | None = None) -> Response:
        visit = self.get_object()
        clinician_id = request.data.get("clinician_id")
        if clinician_id is None:
            return Response({"detail": "clinician_id required"}, status=status.HTTP_400_BAD_REQUEST)
        clinician = Clinician.scoped.filter(pk=clinician_id).first()
        if clinician is None:
            return Response(
                {"detail": "Clinician not found in tenant."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            assign(visit, clinician)
        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(visit).data)

    @action(detail=True, methods=["post"], url_path="check-in")
    def check_in(self, request: Request, pk: str | None = None) -> Response:
        visit = self.get_object()
        try:
            check_in(
                visit,
                lat=float(request.data.get("lat", 0)),
                lon=float(request.data.get("lon", 0)),
            )
        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(visit).data)

    @action(detail=True, methods=["post"], url_path="check-out")
    def check_out(self, request: Request, pk: str | None = None) -> Response:
        visit = self.get_object()
        try:
            check_out(visit, notes=request.data.get("notes", ""))
        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(visit).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request: Request, pk: str | None = None) -> Response:
        visit = self.get_object()
        try:
            cancel(visit, reason=request.data.get("reason", ""))
        except ConflictError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(visit).data)
