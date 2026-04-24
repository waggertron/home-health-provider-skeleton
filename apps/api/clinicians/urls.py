from django.urls import path
from rest_framework.routers import DefaultRouter

from .position_views import ClinicianPositionCreateView, ClinicianPositionLatestView
from .views import ClinicianViewSet

router = DefaultRouter()
router.register("clinicians", ClinicianViewSet, basename="clinicians")

urlpatterns = [
    *router.urls,
    path("positions/", ClinicianPositionCreateView.as_view(), name="positions-create"),
    path(
        "positions/latest/",
        ClinicianPositionLatestView.as_view(),
        name="positions-latest",
    ),
]
