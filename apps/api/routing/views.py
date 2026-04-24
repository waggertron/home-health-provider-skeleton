from rest_framework import mixins, viewsets

from core.permissions import IsSchedulerOrAdmin

from .models import RoutePlan
from .serializers import RoutePlanSerializer


class RoutePlanViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only in Phase 2. Phase 3 Celery task will produce these."""

    serializer_class = RoutePlanSerializer
    permission_classes = [IsSchedulerOrAdmin]

    def get_queryset(self):
        return RoutePlan.scoped.all()
