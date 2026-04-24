from rest_framework import serializers

from .models import Visit


class VisitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Visit
        fields = [
            "id",
            "patient",
            "clinician",
            "window_start",
            "window_end",
            "required_skill",
            "status",
            "check_in_at",
            "check_out_at",
            "ordering_seq",
            "notes",
            "patient_confirmed_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "check_in_at",
            "check_out_at",
            "patient_confirmed_at",
        ]
