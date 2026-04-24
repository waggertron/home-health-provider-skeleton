from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("login", views.login),
    path("refresh", TokenRefreshView.as_view()),
    path("ws-token", views.ws_token),
]
