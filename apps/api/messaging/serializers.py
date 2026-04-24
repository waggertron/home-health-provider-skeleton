from rest_framework import serializers

from .models import SmsOutbox


class SmsOutboxSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsOutbox
        fields = [
            "id",
            "patient",
            "visit",
            "template",
            "body",
            "status",
            "created_at",
            "delivered_at",
            "inbound_reply",
        ]
        read_only_fields = fields
