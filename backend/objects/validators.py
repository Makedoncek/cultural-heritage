import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
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
        raise ValidationError(_('Координати знаходяться за межами території України.'))


def validate_image_size(file):
    """Перевіряє, що файл не перевищує PHOTO_MAX_SIZE_MB."""
    max_bytes = settings.PHOTO_MAX_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(
            _('Файл перевищує %(size)s MB.') % {'size': settings.PHOTO_MAX_SIZE_MB}
        )


def validate_image_format(file):
    """Перевіряє magic bytes через Pillow. НЕ довіряємо Content-Type від клієнта."""
    try:
        file.seek(0)
        with Image.open(file) as img:
            img.verify()
            fmt = (img.format or '').upper()
        file.seek(0)
    except Exception:
        raise ValidationError(_('Файл не є валідним зображенням.'))

    if fmt not in settings.PHOTO_ALLOWED_FORMATS:
        raise ValidationError(
            _('Формат %(fmt)s не підтримується. Дозволені: %(allowed)s.') % {
                'fmt': fmt,
                'allowed': ', '.join(settings.PHOTO_ALLOWED_FORMATS),
            }
        )


def _looks_like_audio(header: bytes) -> bool:
    """Match a container signature for one of the allowed audio formats."""
    if len(header) < 12:
        return False
    if header[:4] == b'RIFF' and header[8:12] == b'WAVE':   # WAV
        return True
    if header[:4] == b'OggS':                                # OGG / Opus
        return True
    if header[:4] == b'\x1a\x45\xdf\xa3':                    # WebM / Matroska (EBML)
        return True
    if header[4:8] == b'ftyp':                               # MP4 / M4A (ISO-BMFF)
        return True
    if header[:3] == b'ID3':                                 # MP3 with ID3 tag
        return True
    if header[0] == 0xFF and (header[1] & 0xE0) == 0xE0:     # MP3 frame sync
        return True
    return False


def validate_audio_format(file):
    """Перевіряє реальний контейнер аудіо за magic-bytes. НЕ довіряємо Content-Type клієнта."""
    file.seek(0)
    header = file.read(12)
    file.seek(0)
    if not _looks_like_audio(header):
        raise ValidationError(_('Файл не є підтримуваним аудіо (mp3, m4a, ogg, wav, webm).'))
