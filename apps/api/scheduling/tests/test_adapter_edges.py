"""Edge cases for scheduling.adapter.build_problem."""

from datetime import UTC, date, datetime, timedelta

import pytest

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from patients.models import Patient
from scheduling.adapter import build_problem
from tenancy.models import Tenant
from visits.models import Visit


@pytest.fixture
def empty_tenant(db):
    return Tenant.objects.create(name="Empty", timezone="UTC")


def test_build_problem_with_no_clinicians_or_visits(empty_tenant):
    problem = build_problem(empty_tenant, date(2026, 4, 24))
    assert problem.clinicians == []
    assert problem.visits == []
    assert problem.distance_matrix == []
    assert problem.allowed_vehicles == []


def test_build_problem_with_clinicians_but_no_visits(empty_tenant):
    u = User.objects.create_user(
        email="rn@empty.demo", password="p", tenant=empty_tenant, role=Role.CLINICIAN
    )
    Clinician.objects.create(
        user=u,
        tenant=empty_tenant,
        credential=Credential.RN,
        home_lat=34.0,
        home_lon=-118.0,
    )
    problem = build_problem(empty_tenant, date(2026, 4, 24))
    assert len(problem.clinicians) == 1
    assert problem.visits == []
    # 1x1 matrix of a single depot node.
    assert len(problem.distance_matrix) == 1
    assert problem.distance_matrix[0][0] == 0
    assert problem.allowed_vehicles == []


def test_build_problem_phlebotomist_requires_exact_match(empty_tenant):
    u_rn = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=empty_tenant, role=Role.CLINICIAN
    )
    u_phleb = User.objects.create_user(
        email="phleb@x.demo", password="p", tenant=empty_tenant, role=Role.CLINICIAN
    )
    Clinician.objects.create(
        user=u_rn,
        tenant=empty_tenant,
        credential=Credential.RN,
        home_lat=34.0,
        home_lon=-118.0,
    )
    Clinician.objects.create(
        user=u_phleb,
        tenant=empty_tenant,
        credential=Credential.PHLEBOTOMIST,
        home_lat=34.1,
        home_lon=-118.1,
    )
    patient = Patient.objects.create(
        tenant=empty_tenant,
        name="P",
        phone="+1",
        address="x",
        lat=34.05,
        lon=-118.0,
        required_skill=Credential.PHLEBOTOMIST,
    )
    day_start = datetime(2026, 4, 24, 8, 0, tzinfo=UTC)
    Visit.objects.create(
        tenant=empty_tenant,
        patient=patient,
        window_start=day_start,
        window_end=day_start + timedelta(hours=2),
        required_skill=Credential.PHLEBOTOMIST,
    )
    problem = build_problem(empty_tenant, date(2026, 4, 24))
    # Clinicians ordered by id: index 0 = RN, index 1 = PHLEBOTOMIST.
    # Phlebotomist visit must allow only the phlebotomist (exact match).
    assert problem.allowed_vehicles[0] == [1]


def test_build_problem_does_not_include_cancelled_visits(empty_tenant):
    from visits.models import VisitStatus

    u = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=empty_tenant, role=Role.CLINICIAN
    )
    Clinician.objects.create(
        user=u,
        tenant=empty_tenant,
        credential=Credential.RN,
        home_lat=34.0,
        home_lon=-118.0,
    )
    p = Patient.objects.create(
        tenant=empty_tenant,
        name="P",
        phone="+1",
        address="x",
        lat=34.01,
        lon=-118.0,
        required_skill=Credential.RN,
    )
    day_start = datetime(2026, 4, 24, 8, 0, tzinfo=UTC)
    Visit.objects.create(
        tenant=empty_tenant,
        patient=p,
        window_start=day_start,
        window_end=day_start + timedelta(hours=2),
        required_skill=Credential.RN,
        status=VisitStatus.CANCELLED,
    )
    problem = build_problem(empty_tenant, date(2026, 4, 24))
    assert problem.visits == []
