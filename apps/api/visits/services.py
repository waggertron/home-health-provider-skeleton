"""Visit state-machine transitions.

Each function enforces the allowed `from` states and stamps the needed
timestamps. A ConflictError is raised when a transition isn't allowed from
the visit's current status so the view layer can map it to HTTP 409.
"""

from datetime import UTC, datetime

from clinicians.models import Clinician
from core.events import publish, visit_reassigned, visit_status_changed

from .models import Visit, VisitStatus


class ConflictError(Exception):
    """Raised when a state transition isn't valid from the current status."""


def _now() -> datetime:
    return datetime.now(UTC)


def assign(visit: Visit, clinician: Clinician) -> Visit:
    if visit.status != VisitStatus.SCHEDULED:
        raise ConflictError(f"Cannot assign visit in status {visit.status} (expected scheduled).")
    visit.clinician = clinician
    visit.status = VisitStatus.ASSIGNED
    visit.save(update_fields=["clinician", "status", "updated_at"])
    publish(visit.tenant_id, visit_reassigned(visit))
    return visit


def check_in(visit: Visit, lat: float, lon: float) -> Visit:
    if visit.status not in (VisitStatus.ASSIGNED, VisitStatus.EN_ROUTE):
        raise ConflictError(
            f"Cannot check in visit in status {visit.status} (expected assigned/en_route)."
        )
    visit.status = VisitStatus.ON_SITE
    visit.check_in_at = _now()
    visit.save(update_fields=["status", "check_in_at", "updated_at"])
    publish(visit.tenant_id, visit_status_changed(visit))
    return visit


def check_out(visit: Visit, notes: str = "") -> Visit:
    if visit.status != VisitStatus.ON_SITE:
        raise ConflictError(f"Cannot check out visit in status {visit.status} (expected on_site).")
    visit.status = VisitStatus.COMPLETED
    visit.check_out_at = _now()
    if notes:
        visit.notes = notes
    visit.save(update_fields=["status", "check_out_at", "notes", "updated_at"])
    publish(visit.tenant_id, visit_status_changed(visit))
    return visit


def cancel(visit: Visit, reason: str = "") -> Visit:
    if visit.status == VisitStatus.COMPLETED:
        raise ConflictError("Cannot cancel a completed visit.")
    visit.status = VisitStatus.CANCELLED
    if reason:
        visit.notes = (visit.notes + "\n" if visit.notes else "") + f"Cancelled: {reason}"
    visit.save(update_fields=["status", "notes", "updated_at"])
    publish(visit.tenant_id, visit_status_changed(visit))
    return visit
