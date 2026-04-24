"""Edge cases for distance helpers — equator, negatives, signs, speeds."""

import math

import pytest

from scheduling.distance import haversine_km, travel_seconds


def test_haversine_symmetry():
    a = haversine_km(34.0, -118.0, 40.7, -74.0)
    b = haversine_km(40.7, -74.0, 34.0, -118.0)
    assert a == pytest.approx(b, rel=1e-9)


def test_haversine_crosses_equator_and_is_positive():
    # Quito (0.18, -78.47) → Nairobi (-1.29, 36.82) ≈ 12,670 km
    d = haversine_km(0.18, -78.47, -1.29, 36.82)
    assert d == pytest.approx(12670, rel=0.02)


def test_haversine_international_date_line_is_short():
    # Two points straddling the date line, 1° apart in longitude near equator.
    d = haversine_km(0.0, 179.5, 0.0, -179.5)
    # 1° at the equator ≈ 111 km.
    assert 100 < d < 125


def test_haversine_negative_coords_equivalent_to_positive_mirror():
    a = haversine_km(34.0, -118.0, 35.0, -117.0)
    b = haversine_km(-34.0, 118.0, -35.0, 117.0)
    assert a == pytest.approx(b, rel=1e-9)


def test_travel_seconds_doubles_when_speed_halves():
    fast = travel_seconds(100.0, mph=40.0)
    slow = travel_seconds(100.0, mph=20.0)
    assert slow == pytest.approx(fast * 2, abs=2)


def test_travel_seconds_rejects_nonpositive_distance():
    assert travel_seconds(-5.0) == 0
    assert travel_seconds(0.0) == 0


def test_travel_seconds_fractional_km_rounds_to_int():
    v = travel_seconds(0.5, mph=40.0)
    assert isinstance(v, int)
    assert v >= 0


def test_haversine_finite_for_extreme_poles():
    d = haversine_km(89.9, 0.0, -89.9, 180.0)
    assert math.isfinite(d)
    assert d > 19000  # close to half-earth
