"""Celery tasks для photo gallery (наприклад, cleanup rejected фото)."""
import logging
from celery import shared_task
from django.utils import timezone

from . import cloudinary_service
from .models import ObjectPhoto

logger = logging.getLogger(__name__)


@shared_task
def cleanup_rejected_photos():
    """Видаляє з Cloudinary і БД фото, відхилені більше PHOTO_REJECTED_RETENTION_DAYS днів тому."""
    expired = ObjectPhoto.objects.filter(
        status=ObjectPhoto.Status.REJECTED,
        rejected_cleanup_at__lte=timezone.now(),
    )
    deleted_count = 0
    for photo in expired:
        try:
            cloudinary_service.delete_photo(photo.cloudinary_public_id)
        except Exception as e:
            logger.error(f'Failed to delete {photo.cloudinary_public_id}: {e}')
            continue
        photo.delete()
        deleted_count += 1
    logger.info(f'cleanup_rejected_photos: deleted {deleted_count} photos')
    return deleted_count
