from rest_framework.routers import DefaultRouter

from .views import SmsOutboxViewSet

router = DefaultRouter()
router.register("sms", SmsOutboxViewSet, basename="sms")

urlpatterns = router.urls
