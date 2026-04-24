from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "id",
            "name",
            "phone",
            "address",
            "lat",
            "lon",
            "required_skill",
            "preferences",
        ]
        read_only_fields = ["id"]
