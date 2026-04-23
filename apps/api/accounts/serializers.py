from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    tenant_id = serializers.IntegerField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "tenant_id"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
