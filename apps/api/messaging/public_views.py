"""Public (no-auth) patient SMS confirmation endpoint (post-v1 #2).

Two routes:
  GET  /p/<token>          → minimal HTML summary + Confirm form
  POST /p/<token>/confirm  → stamps Visit.patient_confirmed_at, publishes
                             visit.patient_confirmed, returns 200

Token errors map to HTTP cleanly:
  - SignatureExpired      → 410 Gone (link too old)
  - BadSignature          → 400 Bad Request (malformed / tampered)
  - Visit not found       → 404
  - Already confirmed     → 410 Gone (single-use)

Authentication is intentionally bypassed — the HMAC-signed token *is*
the auth credential. JWTAuthentication never runs because these views
sit outside the DRF stack.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from django.core.signing import BadSignature, SignatureExpired
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from core.events import publish, visit_patient_confirmed
from messaging.patient_confirm import unsign_visit_token
from visits.models import Visit


def _resolve_visit(token: str) -> tuple[Visit | None, HttpResponse | None]:
    try:
        visit_id = unsign_visit_token(token)
    except SignatureExpired:
        return None, HttpResponse("Link expired.", status=410)
    except BadSignature:
        return None, HttpResponse("Bad token.", status=400)
    visit = Visit.objects.filter(id=visit_id).select_related("patient", "clinician").first()
    if visit is None:
        return None, HttpResponse("Visit not found.", status=404)
    return visit, None


@require_http_methods(["GET"])
def patient_confirm_page(request: HttpRequest, token: str) -> HttpResponse:
    visit, err = _resolve_visit(token)
    if err is not None:
        return err
    visit = cast(Visit, visit)
    patient_name = escape(visit.patient.name)
    clinician = visit.clinician
    clinician_label = escape(clinician.user.email) if clinician is not None else "TBD"
    window = f"{visit.window_start.isoformat()} → {visit.window_end.isoformat()}"
    confirmed_banner = (
        '<p style="color:#0a7c2f"><strong>Already confirmed.</strong></p>'
        if visit.patient_confirmed_at
        else ""
    )
    body = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Confirm visit</title></head>
<body style="font-family:system-ui;max-width:480px;margin:2rem auto;padding:1rem">
  <h1>Hello, {patient_name}</h1>
  <p>Your visit is scheduled for:</p>
  <p><strong>{escape(window)}</strong></p>
  <p>Clinician: {clinician_label}</p>
  {confirmed_banner}
  <form method="post" action="/p/{escape(token)}/confirm">
    <button type="submit" style="padding:0.6rem 1.2rem">Confirm</button>
  </form>
</body></html>"""
    return HttpResponse(body, content_type="text/html; charset=utf-8")


@csrf_exempt
@require_http_methods(["POST"])
def patient_confirm_submit(request: HttpRequest, token: str) -> HttpResponse:
    visit, err = _resolve_visit(token)
    if err is not None:
        return err
    visit = cast(Visit, visit)
    if visit.patient_confirmed_at is not None:
        return HttpResponse("Already confirmed.", status=410)
    visit.patient_confirmed_at = datetime.now(UTC)
    visit.save(update_fields=["patient_confirmed_at"])
    publish(visit.tenant_id, visit_patient_confirmed(visit))
    return JsonResponse({"status": "confirmed", "visit_id": visit.id})
