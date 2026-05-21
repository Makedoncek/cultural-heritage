"""Cloudinary upload/delete для аудіо-наративів (Audio Tours)."""
import uuid

import cloudinary
import cloudinary.uploader

UPLOAD_FOLDER = 'cultural-heritage/audio'
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_FORMATS = ('mp3', 'm4a', 'webm', 'ogg', 'wav')


def upload_audio(file, object_id: int, uploader_id: int) -> dict:
    """Завантажує аудіо у Cloudinary (resource_type='video' охоплює аудіо)
    і повертає dict з public_id, url, duration_seconds.
    """
    response = cloudinary.uploader.upload(
        file,
        resource_type='video',
        folder=f'{UPLOAD_FOLDER}/{object_id}',
        public_id=f'{uploader_id}_{uuid.uuid4().hex}',
        # Cross-browser-safe normalization to mp3 128kbps
        format='mp3',
    )
    return {
        'public_id': response['public_id'],
        'url': response['secure_url'],
        'duration_seconds': int(response.get('duration', 0)),
    }


def delete_audio(public_id: str) -> None:
    """Видаляє аудіо з Cloudinary."""
    cloudinary.uploader.destroy(public_id, resource_type='video')
