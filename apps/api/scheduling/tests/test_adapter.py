from datetime import UTC, date, datetime, timedelta

import pytest

from accounts.models import Role, User
from clinicians.models import Clinician, Credential
from patients.models import Patient
from scheduling.adapter import build_problem
from tenancy.models import Tenant
from visits.models import Visit, VisitStatus


@pytest.fixture
def adapter_fixture(db):
    tenant = Tenant.objects.create(name="Westside", timezone="UTC")
    u_rn = User.objects.create_user(
        email="rn@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    u_ma = User.objects.create_user(
        email="ma@x.demo", password="p", tenant=tenant, role=Role.CLINICIAN
    )
    c_rn = Clinician.objects.create(
        user=u_rn,
        tenant=tenant,
        credential=Credential.RN,
        home_lat=34.0,
        home_lon=-118.0,
    )
    c_ma = Clinician.objects.create(
        user=u_ma,
        tenant=tenant,
        credential=Credential.MA,
        home_lat=34.1,
        home_lon=-118.1,
    )
    the_day = date(2026, 4, 24)
    day_start = datetime(2026, 4, 24, 8, 0, tzinfo=UTC)
    visits = []
    # Five visits: 2×RN, 2×MA, 1×LVN, in that order.
    plan = [
        Credential.RN,
        Credential.RN,
        Credential.MA,
        Credential.MA,
        Credential.LVN,
    ]
    for i, skill in enumerate(plan):
        p = Patient.objects.create(
            tenant=tenant,
            name=f"P{i}",
            phone="+1",
            address="x",
            lat=34.0 + 0.01 * (i + 1),
            lon=-118.0,
            required_skill=skill,
        )
        v = Visit.objects.create(
            tenant=tenant,
            patient=p,
            window_start=day_start + timedelta(hours=i),
            window_end=day_start + timedelta(hours=i + 2),
            required_skill=skill,
        )
        visits.append(v)
    return tenant, the_day, [c_rn, c_ma], visits


def test_build_problem_matrix_shape_is_m_plus_n_squared(adapter_fixture):
    tenant, the_day, _, _ = adapter_fixture
    problem = build_problem(tenant, the_day)
    assert len(problem.clinicians) == 2
    assert len(problem.visits) == 5
    n = len(problem.clinicians) + len(problem.visits)
    assert len(problem.distance_matrix) == n
    for row in problem.distance_matrix:
        assert len(row) == n


def test_build_problem_distance_matrix_diagonal_is_zero(adapter_fixture):
    tenant, the_day, _, _ = adapter_fixture
    problem = build_problem(tenant, the_day)
    n = len(problem.clinicians) + len(problem.visits)
    for i in range(n):
        assert problem.distance_matrix[i][i] == 0


def test_build_problem_allowed_vehicles_respects_credential_hierarchy(adapter_fixture):
    tenant, the_day, _, _ = adapter_fixture
    problem = build_problem(tenant, the_day)
    # Clinicians ordered by id: 0=RN, 1=MA. Visits ordered by window_start:
    # [RN, RN, MA, MA, LVN].
    rn_visit = problem.allowed_vehicles[0]
    ma_visit = problem.allowed_vehicles[2]
    lvn_visit = problem.allowed_vehicles[4]
    assert rn_visit == [0]  # MA clinician cannot serve RN-required
    assert sorted(ma_visit) == [0, 1]  # both can serve MA
    assert lvn_visit == [0]  # MA clinician cannot serve LVN-required


def test_build_problem_excludes_completed_and_other_day_visits(adapter_fixture):
    tenant, the_day, _, visits = adapter_fixture
    # Remove one by completing it.
    v = visits[0]
    v.status = VisitStatus.COMPLETED
    v.save()
    # Add a visit for a different date — should be excluded.
    other_day_start = datetime(2026, 5, 1, 8, 0, tzinfo=UTC)
    Visit.objects.create(
        tenant=tenant,
        patient=visits[0].patient,
        window_start=other_day_start,
        window_end=other_day_start + timedelta(hours=1),
        required_skill=Credential.RN,
    )
    problem = build_problem(tenant, the_day)
    assert len(problem.visits) == 4
