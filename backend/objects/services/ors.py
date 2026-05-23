"""OpenRouteService integration: real-road geometry and TSP-style optimization.

Free tier limits per HeiGIT dashboard (see https://openrouteservice.org/restrictions/).
Sign up without credit card at https://openrouteservice.org/dev/#/signup.
Docs: https://giscience.github.io/openrouteservice/api-reference/
"""
import logging
from typing import Literal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = 'https://api.openrouteservice.org'
DEFAULT_PROFILE = 'foot-walking'
TIMEOUT = 30  # seconds
MAX_OPTIMIZATION_JOBS = 50  # ORS hard limit per /optimization request


class ORSError(Exception):
    """Raised on any ORS-side failure (missing key, HTTP error, malformed payload)."""


def _extract_ors_message(response) -> str:
    """ORS uses two error shapes: Directions returns {'error': {'message': str}},
    Optimization (vroom) returns {'code': int, 'error': str}. Normalize both.
    """
    try:
        body = response.json()
    except Exception:
        return response.text[:200] if response.text else ''
    err = body.get('error')
    if isinstance(err, dict):
        return err.get('message', '') or ''
    if isinstance(err, str):
        return err
    return body.get('message', '') or ''


def _check_key() -> str:
    key = settings.ORS_API_KEY
    if not key:
        raise ORSError('ORS_API_KEY is not configured')
    return key


def get_directions(
    coordinates: list[tuple[float, float]],
    profile: Literal['foot-walking', 'cycling-regular', 'driving-car'] = DEFAULT_PROFILE,
) -> dict:
    """Return real-road geometry between stops in given order.

    Args:
        coordinates: list of (longitude, latitude) tuples — ORS uses lng-first order.
        profile: travel mode.

    Returns:
        dict with:
          geometry — list of [lng, lat] pairs (the polyline along real roads),
          distance_m — total distance in meters,
          duration_s — estimated duration in seconds.
    """
    if len(coordinates) < 2:
        raise ORSError('At least two coordinates required')
    api_key = _check_key()
    # `radiuses: -1` per point asks ORS to snap to the nearest road regardless of distance,
    # avoiding 2010 errors for points in fields / remote villages / unmapped roads.
    response = requests.post(
        f'{BASE_URL}/v2/directions/{profile}/geojson',
        json={
            'coordinates': [[lng, lat] for lng, lat in coordinates],
            'radiuses': [-1] * len(coordinates),
        },
        headers={'Authorization': api_key, 'Content-Type': 'application/json'},
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        logger.warning(f'ORS directions failed: {response.status_code} {response.text[:200]}')
        raise ORSError(_extract_ors_message(response) or f'ORS returned {response.status_code}')
    data = response.json()
    feature = data.get('features', [{}])[0]
    summary = feature.get('properties', {}).get('summary', {})
    return {
        'geometry': feature.get('geometry', {}).get('coordinates', []),
        'distance_m': round(summary.get('distance', 0)),
        'duration_s': round(summary.get('duration', 0)),
    }


def optimize_order(
    coordinates: list[tuple[float, float]],
    profile: Literal['foot-walking', 'cycling-regular', 'driving-car'] = DEFAULT_PROFILE,
) -> list[int]:
    """Return the optimized visit order for the given stops (TSP via vroom engine).

    Uses ORS /v2/optimization which wraps vroom-project (open-source CVRP solver).
    First coordinate is treated as the start; the route is open (no return to start).

    Args:
        coordinates: list of (longitude, latitude) tuples in the *current* order.

    Returns:
        list of original indices in optimized visit order.
        For input [A, B, C, D], a result of [0, 2, 1, 3] means visit A → C → B → D.
    """
    if len(coordinates) < 3:
        # 1 or 2 points — no point optimizing.
        return list(range(len(coordinates)))
    # ORS rejects requests with too many jobs (current cap: 50).
    if len(coordinates) - 1 > MAX_OPTIMIZATION_JOBS:
        raise ORSError(f'Too many stops for ORS Optimization (max {MAX_OPTIMIZATION_JOBS} jobs + 1 start)')
    api_key = _check_key()
    # ORS Optimization expects a vehicle with start point and a list of jobs to visit.
    # We map the first stop to vehicle start, the remainder to jobs.
    start_lng, start_lat = coordinates[0]
    jobs = [
        {'id': i, 'location': [lng, lat]}
        for i, (lng, lat) in enumerate(coordinates[1:], start=1)
    ]
    response = requests.post(
        f'{BASE_URL}/optimization',
        json={
            'jobs': jobs,
            'vehicles': [{
                'id': 1,
                'profile': profile,
                'start': [start_lng, start_lat],
            }],
        },
        headers={'Authorization': api_key, 'Content-Type': 'application/json'},
        timeout=TIMEOUT,
    )
    if response.status_code != 200:
        logger.warning(f'ORS optimize failed: {response.status_code} {response.text[:200]}')
        raise ORSError(_extract_ors_message(response) or f'ORS returned {response.status_code}')
    data = response.json()
    routes = data.get('routes', [])
    if not routes:
        raise ORSError('ORS returned no routes')
    # The first step is the start (vehicle start), then jobs in optimal visit order.
    visited_job_ids = [step['id'] for step in routes[0]['steps'] if step.get('type') == 'job']
    return [0] + visited_job_ids
