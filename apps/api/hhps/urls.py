from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("core.urls")),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/", include("clinicians.urls")),
    path("api/v1/", include("patients.urls")),
]
