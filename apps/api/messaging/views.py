from rest_framework import mixins, viewsets

from core.permissions import IsSchedulerOrAdmin

from .models import SmsOutbox
from .serializers import SmsOutboxSerializer


class SmsOutboxViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only — the ops console's SMS log. Celery writes; humans read."""

    serializer_class = SmsOutboxSerializer
    permission_classes = [IsSchedulerOrAdmin]

    def get_queryset(self):
        return SmsOutbox.scoped.all().order_by("-created_at")
