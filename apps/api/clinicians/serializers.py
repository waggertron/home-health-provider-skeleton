from rest_framework import serializers

from .models import Clinician


class ClinicianSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = Clinician
        fields = [
            "id",
            "email",
            "credential",
            "skills",
            "home_lat",
            "home_lon",
            "shift_windows",
        ]
        read_only_fields = ["id", "email"]
