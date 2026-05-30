"""Signal handlers for status transitions and cascading cleanup."""
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save, pre_delete
from django.dispatch import receiver

from .models import CulturalObject, ObjectPhoto, ObjectAudio, UserPreference

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def _create_user_preference(sender, instance, created, **kwargs):
    """Auto-create a UserPreference row for every new user with the default language."""
    if created:
        UserPreference.objects.get_or_create(
            user=instance,
            defaults={'language': settings.LANGUAGE_CODE},
        )


@receiver(pre_save, sender=CulturalObject)
def _store_old_status(sender, instance, **kwargs):
    """Запам'ятовує попередній status для post_save, який зрівняє зі станом після save."""
    if instance.pk:
        try:
            instance._old_status = (
                CulturalObject.objects.only('status').get(pk=instance.pk).status
            )
        except CulturalObject.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(pre_save, sender=CulturalObject)
def _sync_archived_at(sender, instance, **kwargs):
    """Синхронізує `archived_at` зі статусом при будь-якому save:
       - status стає `archived` → archived_at = now
       - status вже не `archived` → archived_at = None
    """
    from django.utils import timezone
    if instance.status == CulturalObject.Status.ARCHIVED:
        if instance.archived_at is None:
            instance.archived_at = timezone.now()
    else:
        if instance.archived_at is not None:
            instance.archived_at = None


@receiver(post_save, sender=CulturalObject)
def _trigger_status_emails(sender, instance, created, raw, **kwargs):
    """При переході status з pending у approved розсилає email-и автору і підписникам."""
    if raw or created:
        return
    old = getattr(instance, '_old_status', None)
    if old == CulturalObject.Status.PENDING and instance.status == CulturalObject.Status.APPROVED:
        from .email import send_status_notification, send_follower_notifications
        if instance.author.email:
            send_status_notification.delay(instance.id, 'approved')
        send_follower_notifications.delay(instance.id)


@receiver(pre_save, sender=ObjectPhoto)
def _reset_photo_status_on_caption_change(sender, instance, **kwargs):
    """Якщо caption approved/rejected фото редагується — скинути status у pending.

    Винятки:
      - Якщо в тому ж save status змінено явно (admin form з кількома полями) — не чіпати.
      - Якщо виставлено `instance._skip_status_reset` (admin edit) — не чіпати.
    """
    if not instance.pk:
        return
    if getattr(instance, '_skip_status_reset', False):
        return
    try:
        old = ObjectPhoto.objects.only('caption', 'status').get(pk=instance.pk)
    except ObjectPhoto.DoesNotExist:
        return
    if old.caption == instance.caption:
        return
    if old.status != instance.status:
        return  # status явно змінено в цьому save — admin сам вирішує
    if instance.status in (ObjectPhoto.Status.APPROVED, ObjectPhoto.Status.REJECTED):
        instance.status = ObjectPhoto.Status.PENDING
        instance.moderated_at = None
        instance.rejected_cleanup_at = None


@receiver(pre_delete, sender=ObjectAudio)
def _cleanup_cloudinary_on_audio_delete(sender, instance, **kwargs):
    """Видаляє Cloudinary-аудіо при будь-якому видаленні ObjectAudio.
    Виконується синхронно — аудіо file rate теж невеликий.
    """
    if not instance.cloudinary_public_id:
        return
    try:
        from . import cloudinary_audio_service
        cloudinary_audio_service.delete_audio(instance.cloudinary_public_id)
    except Exception:
        logger.exception('Failed to delete Cloudinary audio %s', instance.cloudinary_public_id)


@receiver(pre_delete, sender=ObjectPhoto)
def _cleanup_cloudinary_on_photo_delete(sender, instance, **kwargs):
    """Видаляє Cloudinary-файл при будь-якому видаленні ObjectPhoto.

    Спрацьовує і на admin «Видалити обрані», і на API DELETE,
    і на CASCADE при видаленні CulturalObject/User.
    Виконується асинхронно через Celery-task з retry — щоб HTTP-call
    до Cloudinary не блокував request і пережив тимчасові збої API.
    """
    if not instance.cloudinary_public_id:
        return
    from .tasks import delete_cloudinary_file
    delete_cloudinary_file.delay(instance.cloudinary_public_id)
