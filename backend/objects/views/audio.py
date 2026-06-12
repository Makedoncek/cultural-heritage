"""Audio narratives для культурного об'єкта (nested під /api/objects/<obj_pk>/audios/)."""
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .. import cloudinary_audio_service
from ..models import CulturalObject, ObjectAudio
from ..serializers import AudioUploadSerializer, ObjectAudioSerializer
from ._common import require_owner_or_staff

MAX_AUDIOS_PER_OBJECT = 10

OWNER_ONLY_MSG = 'Дозволено лише автору або адміністратору.'


class _AudioLimitExceeded(Exception):
    """Internal: roll back an upload whose row would exceed the per-object limit."""


class ObjectAudioViewSet(viewsets.ViewSet):
    """Audio narratives для культурного об'єкта.

    Endpoints:
      GET    /api/objects/<obj_pk>/audios/             — list approved (public) + own pending/rejected
      POST   /api/objects/<obj_pk>/audios/             — upload (multipart), copyright_confirmed=true
      GET    /api/objects/<obj_pk>/audios/<pk>/        — detail
      PATCH  /api/objects/<obj_pk>/audios/<pk>/        — edit metadata (title/narrator/language)
      DELETE /api/objects/<obj_pk>/audios/<pk>/        — author or admin
      POST   /api/objects/<obj_pk>/audios/<pk>/play/   — increment plays_count

    Moderation (approve/reject) is performed exclusively via Django Admin.
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'play'):
            return [AllowAny()]
        return [IsAuthenticated()]

    def _get_object(self, obj_pk):
        return get_object_or_404(CulturalObject, pk=obj_pk)

    def _get_audio(self, obj_pk, pk):
        return get_object_or_404(ObjectAudio, pk=pk, cultural_object_id=obj_pk)

    def list(self, request, obj_pk=None):
        cultural_object = self._get_object(obj_pk)
        user = request.user
        # Archived narratives are hidden from the public object view (managed in "My contributions").
        qs = (ObjectAudio.objects.filter(cultural_object=cultural_object)
              .exclude(status=ObjectAudio.Status.ARCHIVED)
              .select_related('uploaded_by'))
        language = request.query_params.get('language')
        if language:
            qs = qs.filter(language=language)
        if user.is_authenticated and user.is_staff:
            pass  # show everything (except archived, excluded above)
        elif user.is_authenticated:
            qs = qs.filter(Q(status=ObjectAudio.Status.APPROVED) | Q(uploaded_by=user))
        else:
            qs = qs.filter(status=ObjectAudio.Status.APPROVED)
        return Response(ObjectAudioSerializer(qs, many=True).data)

    def retrieve(self, request, obj_pk=None, pk=None):
        audio = self._get_audio(obj_pk, pk)
        user = request.user
        if audio.status != ObjectAudio.Status.APPROVED:
            if not user.is_authenticated or (audio.uploaded_by_id != user.id and not user.is_staff):
                return Response({'detail': _('Не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
        return Response(ObjectAudioSerializer(audio).data)

    @staticmethod
    def _active_audio_count(cultural_object):
        # Rejected/archived narratives don't count toward the limit (mirrors photo logic),
        # so a rejection or archive frees the slot for a re-submission.
        return cultural_object.audios.exclude(
            status__in=[ObjectAudio.Status.REJECTED, ObjectAudio.Status.ARCHIVED]
        ).count()

    def create(self, request, obj_pk=None):
        cultural_object = self._get_object(obj_pk)
        serializer = AudioUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Cheap pre-check before the slow upload; the authoritative re-check is under the lock.
        if self._active_audio_count(cultural_object) >= MAX_AUDIOS_PER_OBJECT:
            return Response(
                {'detail': _("Об'єкт може мати максимум 10 аудіо-наративів.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        uploaded = cloudinary_audio_service.upload_audio(
            serializer.validated_data['audio'],
            object_id=cultural_object.id,
            uploader_id=request.user.id,
        )
        try:
            # Row-lock the parent so parallel uploads can't bypass the per-object limit.
            with transaction.atomic():
                CulturalObject.objects.select_for_update().get(pk=cultural_object.pk)
                if self._active_audio_count(cultural_object) >= MAX_AUDIOS_PER_OBJECT:
                    raise _AudioLimitExceeded()
                audio = ObjectAudio.objects.create(
                    cultural_object=cultural_object,
                    uploaded_by=request.user,
                    cloudinary_public_id=uploaded['public_id'],
                    cloudinary_url=uploaded['url'],
                    duration_seconds=uploaded['duration_seconds'],
                    language=serializer.validated_data['language'],
                    title=serializer.validated_data['title'],
                    narrator_name=serializer.validated_data.get('narrator_name', ''),
                    copyright_confirmed=True,
                )
        except _AudioLimitExceeded:
            # No row created → pre_delete-signal won't fire; remove the orphan upload.
            try:
                cloudinary_audio_service.delete_audio(uploaded['public_id'])
            except Exception:
                pass
            return Response(
                {'detail': _("Об'єкт може мати максимум 10 аудіо-наративів.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(ObjectAudioSerializer(audio).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, obj_pk=None, pk=None):
        audio = self._get_audio(obj_pk, pk)
        require_owner_or_staff(request, audio.uploaded_by_id, OWNER_ONLY_MSG)
        # User cannot edit moderation fields; restrict to safe set.
        editable = {'title', 'narrator_name', 'language'}
        update_kwargs = {k: v for k, v in request.data.items() if k in editable}
        if not update_kwargs:
            return Response(ObjectAudioSerializer(audio).data)
        for k, v in update_kwargs.items():
            setattr(audio, k, v)
        # Edits by non-admins push back to pending (re-moderation) — both from approved and rejected.
        if not request.user.is_staff and audio.status in (ObjectAudio.Status.APPROVED, ObjectAudio.Status.REJECTED):
            audio.status = ObjectAudio.Status.PENDING
            audio.moderated_at = None
            audio.moderation_note = ''
        audio.save()
        return Response(ObjectAudioSerializer(audio).data)

    def destroy(self, request, obj_pk=None, pk=None):
        audio = self._get_audio(obj_pk, pk)
        require_owner_or_staff(request, audio.uploaded_by_id, OWNER_ONLY_MSG)
        audio.delete()  # pre_delete-signal cleans up Cloudinary
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def archive(self, request, obj_pk=None, pk=None):
        """Owner soft-removes their narrative (any status → archived; hidden from public)."""
        audio = self._get_audio(obj_pk, pk)
        require_owner_or_staff(request, audio.uploaded_by_id, OWNER_ONLY_MSG)
        audio.status = ObjectAudio.Status.ARCHIVED
        audio.save(update_fields=['status', 'updated_at'])
        return Response(ObjectAudioSerializer(audio).data)

    @action(detail=True, methods=['post'])
    def restore(self, request, obj_pk=None, pk=None):
        """Owner restores an archived narrative → back to moderation (pending)."""
        audio = self._get_audio(obj_pk, pk)
        require_owner_or_staff(request, audio.uploaded_by_id, OWNER_ONLY_MSG)
        if audio.status != ObjectAudio.Status.ARCHIVED:
            return Response({'detail': _('Відновити можна лише архівований запис.')},
                            status=status.HTTP_400_BAD_REQUEST)
        audio.status = ObjectAudio.Status.PENDING
        audio.save(update_fields=['status', 'updated_at'])
        return Response(ObjectAudioSerializer(audio).data)

    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def play(self, request, obj_pk=None, pk=None):
        audio = self._get_audio(obj_pk, pk)
        if audio.status != ObjectAudio.Status.APPROVED:
            return Response({'detail': _('Цей аудіонарратив недоступний.')},
                            status=status.HTTP_403_FORBIDDEN)
        # Don't inflate the counter with self-plays — the uploader's own listens don't count.
        if request.user.is_authenticated and request.user.id == audio.uploaded_by_id:
            return Response({'detail': 'self-play not counted'})
        ObjectAudio.objects.filter(pk=audio.pk).update(plays_count=F('plays_count') + 1)
        return Response({'detail': 'ok'})
