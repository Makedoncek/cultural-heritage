"""Geospatial helpers — Haversine distance for duplicate-detection."""
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000  # WGS-84 mean radius in meters


def haversine_distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points on Earth, in meters.

    Uses the Haversine formula:
        a = sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlng/2)
        d = 2·R·asin(√a)

    Accurate to ~0.5% across Earth-scale distances; better numerical stability
    than the spherical law of cosines for small distances (the use case here).
    """
    lat1_r, lng1_r, lat2_r, lng2_r = map(radians, (lat1, lng1, lat2, lng2))
    d_lat = lat2_r - lat1_r
    d_lng = lng2_r - lng1_r
    a = sin(d_lat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(d_lng / 2) ** 2
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


def find_nearby_objects(latitude: float, longitude: float, radius_m: float = 100.0,
                        exclude_id: int | None = None):
    """Return approved CulturalObjects within `radius_m` of the given point.

    First filters by a rough bounding box (cheap SQL) — needed because Haversine
    is not indexable. Then refines with exact Haversine distance in Python.
    For our scale (~1000s of objects) this is sub-millisecond; PostGIS would be
    the proper choice past ~100K objects.
    """
    from ..models import CulturalObject
    # 1 degree latitude ≈ 111_000 m everywhere; longitude ≈ 111_000·cos(lat)
    deg_lat = radius_m / 111_000
    deg_lng = radius_m / (111_000 * max(cos(radians(latitude)), 0.01))
    qs = CulturalObject.objects.filter(
        status=CulturalObject.Status.APPROVED,
        latitude__gte=latitude - deg_lat,
        latitude__lte=latitude + deg_lat,
        longitude__gte=longitude - deg_lng,
        longitude__lte=longitude + deg_lng,
    )
    if exclude_id is not None:
        qs = qs.exclude(pk=exclude_id)
    result = []
    for obj in qs:
        distance = haversine_distance_m(latitude, longitude, float(obj.latitude), float(obj.longitude))
        if distance <= radius_m:
            result.append((obj, distance))
    result.sort(key=lambda x: x[1])
    return result
