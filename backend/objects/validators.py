import json
from pathlib import Path

from django.core.exceptions import ValidationError
from shapely.geometry import shape, Point
from shapely.prepared import prep

_DATA_DIR = Path(__file__).resolve().parent / 'data'
_GEOJSON_PATH = _DATA_DIR / 'ukraine_border.json'

with open(_GEOJSON_PATH, encoding='utf-8') as f:
    _geojson = json.load(f)

_ukraine_polygon = shape(_geojson['features'][0]['geometry'])
_ukraine_prepared = prep(_ukraine_polygon)


def is_within_ukraine(latitude, longitude) -> bool:
    point = Point(float(longitude), float(latitude))  # Shapely: (x=lng, y=lat)
    return _ukraine_prepared.contains(point)


def validate_coordinates_within_ukraine(latitude, longitude):
    if not is_within_ukraine(latitude, longitude):
        raise ValidationError('Координати знаходяться за межами території України.')
