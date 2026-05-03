import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError
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


def validate_image_size(file):
    """Перевіряє, що файл не перевищує PHOTO_MAX_SIZE_MB."""
    max_bytes = settings.PHOTO_MAX_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(
            f'Файл перевищує {settings.PHOTO_MAX_SIZE_MB} MB.'
        )


def validate_image_format(file):
    """Перевіряє magic bytes через Pillow. НЕ довіряємо Content-Type від клієнта."""
    try:
        file.seek(0)
        with Image.open(file) as img:
            img.verify()
            fmt = (img.format or '').upper()
        file.seek(0)
    except (UnidentifiedImageError, Exception):
        raise ValidationError('Файл не є валідним зображенням.')

    if fmt not in settings.PHOTO_ALLOWED_FORMATS:
        raise ValidationError(
            f'Формат {fmt} не підтримується. Дозволені: {", ".join(settings.PHOTO_ALLOWED_FORMATS)}.'
        )
