"""Distance helpers for the VRP solver.

Haversine great-circle distance and a fixed-speed travel-time estimate.
Known limitation: road network effects are ignored (see docs/architecture.md §13).
"""

from __future__ import annotations

import math

_EARTH_RADIUS_KM = 6371.0088
_KM_PER_MILE = 1.609344


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points in kilometers."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return _EARTH_RADIUS_KM * c


def travel_seconds(km: float, mph: float = 40.0) -> int:
    """Travel time in seconds for a straight-line distance at a fixed average speed."""
    if km <= 0:
        return 0
    kph = mph * _KM_PER_MILE
    return int(round((km / kph) * 3600))
