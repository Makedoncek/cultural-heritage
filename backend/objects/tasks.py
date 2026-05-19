"""Celery tasks для photo gallery (наприклад, cleanup rejected фото)."""
import logging
from celery import shared_task
from django.utils import timezone

from datetime import timedelta

from . import cloudinary_service
from .models import InaccuracyReport, ObjectPhoto

INACCURACY_REPORT_RETENTION_DAYS = 30

logger = logging.getLogger(__name__)


# Параметри retry для Cloudinary-delete: експоненційний backoff
# (1s → 2s → 4s → 8s → 16s → 32s..., max 1 година) з jitter.
# 7 спроб ≈ покриває ~2 години переривчастого Cloudinary-uptime.
CLOUDINARY_DELETE_RETRY_KWARGS = dict(
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True,
    max_retries=7,
)


@shared_task(**CLOUDINARY_DELETE_RETRY_KWARGS)
def delete_cloudinary_file(public_id: str) -> None:
    """Видаляє файл з Cloudinary з retry-логікою.

    Викликається з pre_delete-signal на ObjectPhoto — щоб HTTP-call
    до Cloudinary не блокував request-цикл і отримував повторні спроби
    при тимчасових збоях API.
    """
    cloudinary_service.delete_photo(public_id)
    logger.info(f'Cloudinary file deleted: {public_id}')


@shared_task
def cleanup_rejected_photos():
    """Видаляє з БД фото, відхилені більше PHOTO_REJECTED_RETENTION_DAYS днів тому.

    Cloudinary-файл прибирає pre_delete-signal у objects/signals.py.
    """
    expired = ObjectPhoto.objects.filter(
        status=ObjectPhoto.Status.REJECTED,
        rejected_cleanup_at__lte=timezone.now(),
    )
    deleted_count = 0
    for photo in expired:
        try:
            photo.delete()
        except Exception as e:
            logger.error(f'Failed to delete photo {photo.cloudinary_public_id}: {e}')
            continue
        deleted_count += 1
    logger.info(f'cleanup_rejected_photos: deleted {deleted_count} photos')
    return deleted_count


@shared_task
def cleanup_processed_inaccuracy_reports():
    """Видаляє repords зі статусом resolved/dismissed, оброблені понад
    INACCURACY_REPORT_RETENTION_DAYS днів тому.

    Залишаємо у БД лише pending + свіжо-оброблені (≤ retention) — щоб адмін
    бачив нещодавні рішення, але не накопичував архів вирішених проблем.
    """
    cutoff = timezone.now() - timedelta(days=INACCURACY_REPORT_RETENTION_DAYS)
    expired = InaccuracyReport.objects.filter(
        status__in=[InaccuracyReport.Status.RESOLVED, InaccuracyReport.Status.DISMISSED],
        resolved_at__lte=cutoff,
    )
    deleted_count, _ = expired.delete()
    logger.info(f'cleanup_processed_inaccuracy_reports: deleted {deleted_count} reports')
    return deleted_count
