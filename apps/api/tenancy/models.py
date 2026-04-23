from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=200, unique=True)
    timezone = models.CharField(max_length=64, default="America/Los_Angeles")
    home_base_lat = models.FloatField(null=True, blank=True)
    home_base_lon = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
