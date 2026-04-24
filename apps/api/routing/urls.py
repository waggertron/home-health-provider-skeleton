from rest_framework.routers import DefaultRouter

from .views import RoutePlanViewSet

router = DefaultRouter()
router.register("routeplans", RoutePlanViewSet, basename="routeplans")

urlpatterns = router.urls
