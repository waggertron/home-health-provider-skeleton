import pytest

from scheduling.distance import haversine_km, travel_seconds


def test_haversine_zero_when_points_coincide():
    assert haversine_km(34.0, -118.0, 34.0, -118.0) == pytest.approx(0.0, abs=1e-6)


def test_haversine_la_to_sf_is_within_tolerance():
    # LA (34.0522, -118.2437) → SF (37.7749, -122.4194) is ~559 km.
    d = haversine_km(34.0522, -118.2437, 37.7749, -122.4194)
    assert d == pytest.approx(559.0, rel=0.02)  # ±2%


def test_haversine_la_basin_neighbors_is_a_few_km():
    # Santa Monica (34.0195, -118.4912) → LAX area (33.9416, -118.4085)
    d = haversine_km(34.0195, -118.4912, 33.9416, -118.4085)
    assert 8 < d < 14


def test_haversine_antipode_is_half_the_earths_circumference():
    # Earth's circumference is ~40,075 km; antipodal points are ~20,037 km apart.
    d = haversine_km(0, 0, 0, 180)
    assert d == pytest.approx(20015, rel=0.01)


def test_travel_seconds_is_km_divided_by_mph_in_seconds():
    # 64 km at 40 mph (64.3737 km/h) ≈ 3579 seconds.
    assert travel_seconds(64.0, mph=40.0) == pytest.approx(3579, abs=5)


def test_travel_seconds_zero_distance_is_zero():
    assert travel_seconds(0.0) == 0
