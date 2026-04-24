from django.urls import path

from .views import OptimizeDayView

urlpatterns = [
    path("schedule/<str:iso_date>/optimize", OptimizeDayView.as_view(), name="schedule-optimize"),
]
