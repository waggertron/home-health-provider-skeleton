from rest_framework import mixins, viewsets

from core.permissions import IsSchedulerOrAdmin

from .models import Clinician
from .serializers import ClinicianSerializer


class ClinicianViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only in Phase 2. Clinicians are seeded, not created via API."""

    serializer_class = ClinicianSerializer
    permission_classes = [IsSchedulerOrAdmin]

    def get_queryset(self):
        return Clinician.scoped.all()
