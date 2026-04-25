from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    tenant_id = serializers.IntegerField()
    clinician_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "tenant_id", "clinician_id"]

    def get_clinician_id(self, user: User) -> int | None:
        # OneToOne reverse accessor; only present when role == clinician.
        clinician = getattr(user, "clinician_profile", None)
        return clinician.id if clinician is not None else None


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
