from core.permissions import IsSchedulerOrAdmin
from core.viewsets import BaseTenantViewSet

from .models import Patient
from .serializers import PatientSerializer


class PatientViewSet(BaseTenantViewSet):
    """Full CRUD for Patients. Scheduler/admin only."""

    serializer_class = PatientSerializer
    permission_classes = [IsSchedulerOrAdmin]

    def get_queryset(self):
        return Patient.scoped.all()
