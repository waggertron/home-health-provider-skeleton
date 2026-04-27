from django.urls import include, path

from messaging.public_views import patient_confirm_page, patient_confirm_submit

urlpatterns = [
    path("api/v1/", include("core.urls")),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/", include("clinicians.urls")),
    path("api/v1/", include("patients.urls")),
    path("api/v1/", include("visits.urls")),
    path("api/v1/", include("routing.urls")),
    path("api/v1/", include("messaging.urls")),
    path("api/v1/", include("scheduling.urls")),
    # Public patient SMS confirmation links (no auth — HMAC-signed token IS the credential).
    path("p/<str:token>", patient_confirm_page),
    path("p/<str:token>/confirm", patient_confirm_submit),
]
