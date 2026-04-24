from rest_framework.routers import DefaultRouter

from .views import ClinicianViewSet

router = DefaultRouter()
router.register("clinicians", ClinicianViewSet, basename="clinicians")

urlpatterns = router.urls
