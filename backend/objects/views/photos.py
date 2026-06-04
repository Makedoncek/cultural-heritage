"""Photo management for cultural objects (nested under /api/objects/<object_pk>/photos/)."""
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .. import cloudinary_service
from ..models import CulturalObject, ObjectPhoto
from ..permissions import IsObjectAuthor, IsPhotoCaptionEditor, IsPhotoUploaderOrAdmin
from ..serializers import ObjectPhotoSerializer
from ..throttles import PhotoUploadThrottle
from ..validators import validate_image_format, validate_image_size
from ._common import require_owner_or_staff

logger = logging.getLogger(__name__)

# Statuses that don't occupy limit slots: a rejection or archive frees the slot.
INACTIVE_PHOTO_STATUSES = ('rejected', 'archived')


class _PhotoLimitExceeded(Exception):
    """Внутрішня помилка для скасування транзакції upload-у при перевищенні ліміту."""

    def __init__(self, code: str, limit: int):
        self.code = code
        self.limit = limit


class ObjectPhotoViewSet(viewsets.GenericViewSet):
    """Управління фото культурного об'єкта (nested під /api/objects/<object_pk>/photos/)."""
    serializer_class = ObjectPhotoSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action == 'reorder':
            return [IsObjectAuthor()]
        if self.action == 'destroy':
            return [IsAuthenticated(), IsPhotoUploaderOrAdmin()]
        if self.action == 'partial_update':
            return [IsAuthenticated(), IsPhotoCaptionEditor()]
        return [AllowAny()]

    def get_throttles(self):
        if self.action == 'create':
            return [PhotoUploadThrottle()]
        return super().get_throttles()

    def _get_object(self):
        return get_object_or_404(
            CulturalObject.objects.exclude(status='archived'),
            pk=self.kwargs['object_pk'],
        )

    def list(self, request, *args, **kwargs):
        cultural_object = self._get_object()
        # Archived photos are hidden from the public object view (managed in "My contributions").
        qs = ObjectPhoto.objects.filter(cultural_object=cultural_object).exclude(status='archived')

        user = request.user
        if not user.is_authenticated:
            qs = qs.filter(status='approved')
        elif not user.is_staff:
            qs = qs.filter(Q(uploaded_by=user) | Q(status='approved'))

        serializer = ObjectPhotoSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        cultural_object = self._get_object()
        is_author = cultural_object.author_id == request.user.id

        if not is_author and cultural_object.status != 'approved':
            return Response(
                {'detail': 'Можна додавати фото лише до затверджених об\'єктів.'},
                status=403,
            )

        image = request.FILES.get('image')
        if not image:
            return Response({'detail': 'Поле image є обов\'язковим.'}, status=400)

        try:
            validate_image_size(image)
            validate_image_format(image)
        except ValidationError as e:
            return Response({'detail': e.message if hasattr(e, 'message') else str(e)}, status=400)

        max_user, limit_error = self._check_photo_limits(cultural_object, request.user, is_author)
        if limit_error:
            return limit_error

        try:
            uploaded = cloudinary_service.upload_photo(image)
        except Exception as e:
            logger.exception('Cloudinary upload failed: %s', e)
            return Response(
                {'detail': 'Не вдалося завантажити фото на сервер. Спробуйте пізніше.'},
                status=500,
            )

        photo, store_error = self._store_photo_locked(cultural_object, request, uploaded, is_author, max_user)
        if store_error:
            return store_error
        return Response(ObjectPhotoSerializer(photo).data, status=201)

    @staticmethod
    def _limit_error_response(code, limit):
        if code == 'user_limit_exceeded':
            detail = f'Ліміт {limit} фото на цей об\'єкт вичерпано.'
        else:
            detail = f'Об\'єкт уже містить максимум {limit} фото.'
        return Response({'detail': detail, 'code': code}, status=400)

    def _check_photo_limits(self, cultural_object, user, is_author):
        """Pre-upload limit checks. Returns (max_user, error_response_or_None)."""
        user_count = ObjectPhoto.objects.filter(
            cultural_object=cultural_object,
            uploaded_by=user,
        ).exclude(status__in=INACTIVE_PHOTO_STATUSES).count()
        max_user = (
            settings.PHOTO_MAX_PER_AUTHOR if is_author
            else settings.PHOTO_MAX_PER_CONTRIBUTOR
        )
        if user_count >= max_user:
            return max_user, self._limit_error_response('user_limit_exceeded', max_user)
        total = ObjectPhoto.objects.filter(
            cultural_object=cultural_object,
        ).exclude(status__in=INACTIVE_PHOTO_STATUSES).count()
        if total >= settings.PHOTO_MAX_PER_OBJECT:
            return max_user, self._limit_error_response('object_full', settings.PHOTO_MAX_PER_OBJECT)
        return max_user, None

    def _store_photo_locked(self, cultural_object, request, uploaded, is_author, max_user):
        """Atomic re-check (row-lock) + create. Returns (photo_or_None, error_response_or_None).

        The row-lock on the parent prevents a race where parallel uploads bypass the
        limits checked before the Cloudinary upload.
        """
        from django.db import transaction
        try:
            with transaction.atomic():
                CulturalObject.objects.select_for_update().get(pk=cultural_object.pk)

                user_count_locked = ObjectPhoto.objects.filter(
                    cultural_object=cultural_object,
                    uploaded_by=request.user,
                ).exclude(status__in=INACTIVE_PHOTO_STATUSES).count()
                if user_count_locked >= max_user:
                    raise _PhotoLimitExceeded('user_limit_exceeded', max_user)

                total_locked = ObjectPhoto.objects.filter(
                    cultural_object=cultural_object,
                ).exclude(status__in=INACTIVE_PHOTO_STATUSES).count()
                if total_locked >= settings.PHOTO_MAX_PER_OBJECT:
                    raise _PhotoLimitExceeded('object_full', settings.PHOTO_MAX_PER_OBJECT)

                existing_orders = list(
                    ObjectPhoto.objects.filter(
                        cultural_object=cultural_object,
                    ).values_list('order', flat=True)
                )
                order = max(existing_orders, default=-1) + 1

                photo = ObjectPhoto.objects.create(
                    cultural_object=cultural_object,
                    uploaded_by=request.user,
                    cloudinary_public_id=uploaded['public_id'],
                    image_url=uploaded['image_url'],
                    thumbnail_url=uploaded['thumbnail_url'],
                    caption=request.data.get('caption', '')[:200],
                    is_author_photo=is_author,
                    order=order,
                )
            return photo, None
        except _PhotoLimitExceeded as e:
            # rollback: видалити Cloudinary-файл (бо ObjectPhoto не створено,
            # тож pre_delete-signal не спрацює)
            try:
                cloudinary_service.delete_photo(uploaded['public_id'])
            except Exception:
                pass
            return None, self._limit_error_response(e.code, e.limit)

    def destroy(self, request, *args, **kwargs):
        cultural_object = self._get_object()
        photo = get_object_or_404(ObjectPhoto, pk=kwargs['pk'], cultural_object=cultural_object)
        self.check_object_permissions(request, photo)
        photo.delete()  # pre_delete signal у objects/signals.py чистить Cloudinary
        return Response(status=204)

    def partial_update(self, request, *args, **kwargs):
        cultural_object = self._get_object()
        photo = get_object_or_404(ObjectPhoto, pk=kwargs['pk'], cultural_object=cultural_object)
        self.check_object_permissions(request, photo)

        caption = request.data.get('caption')
        if caption is not None:
            if len(caption) > 200:
                return Response({'detail': 'Caption перевищує 200 символів.'}, status=400)
            if caption != photo.caption:
                photo.caption = caption
                # pre_save signal у objects/signals.py скидає status у pending,
                # якщо approved/rejected фото отримує нову caption.
                # Admin-edit обходить reset через _skip_status_reset.
                if request.user.is_staff:
                    photo._skip_status_reset = True
                photo.save()

        return Response(ObjectPhotoSerializer(photo).data)

    @action(detail=True, methods=['post'], url_path='archive', permission_classes=[IsAuthenticated])
    def archive(self, request, *args, **kwargs):
        """Owner soft-removes their photo (any status → archived; hidden from public)."""
        cultural_object = self._get_object()
        photo = get_object_or_404(ObjectPhoto, pk=kwargs['pk'], cultural_object=cultural_object)
        require_owner_or_staff(request, photo.uploaded_by_id, 'Дозволено лише автору або адміністратору.')
        photo._skip_status_reset = True
        photo.status = ObjectPhoto.Status.ARCHIVED
        photo.save(update_fields=['status'])
        return Response(ObjectPhotoSerializer(photo).data)

    @action(detail=True, methods=['post'], url_path='restore', permission_classes=[IsAuthenticated])
    def restore(self, request, *args, **kwargs):
        """Owner restores an archived photo → back to moderation (pending)."""
        cultural_object = self._get_object()
        photo = get_object_or_404(ObjectPhoto, pk=kwargs['pk'], cultural_object=cultural_object)
        require_owner_or_staff(request, photo.uploaded_by_id, 'Дозволено лише автору або адміністратору.')
        if photo.status != ObjectPhoto.Status.ARCHIVED:
            return Response({'detail': _('Відновити можна лише архівоване фото.')}, status=400)
        photo._skip_status_reset = True
        photo.status = ObjectPhoto.Status.PENDING
        photo.save(update_fields=['status'])
        return Response(ObjectPhotoSerializer(photo).data)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request, *args, **kwargs):
        cultural_object = self._get_object()
        items = request.data.get('order', [])
        if not isinstance(items, list):
            return Response({'detail': 'order must be a list'}, status=400)

        photo_ids = [item.get('id') for item in items]
        photos = list(ObjectPhoto.objects.filter(
            id__in=photo_ids,
            cultural_object=cultural_object,
        ))
        if len(photos) != len(photo_ids):
            return Response({'detail': 'Деякі фото не знайдено в цьому об\'єкті.'}, status=400)

        by_id = {p.id: p for p in photos}
        for item in items:
            p = by_id[item['id']]
            p.order = int(item['order'])
        ObjectPhoto.objects.bulk_update(photos, ['order'])
        return Response({'detail': 'ok'})
