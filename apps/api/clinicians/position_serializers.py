from rest_framework import serializers

from .models import ClinicianPosition


class ClinicianPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicianPosition
        fields = ["id", "clinician", "lat", "lon", "ts", "heading", "speed"]
        # clinician is server-derived from the authenticated user on POST.
        read_only_fields = ["id", "clinician"]
