from rest_framework import serializers

from .models import RoutePlan


class RoutePlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoutePlan
        fields = ["id", "clinician", "date", "visits_ordered", "solver_metadata"]
        read_only_fields = ["id"]
