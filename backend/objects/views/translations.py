"""Management of the user's own translation proposals (objects and routes).

Submission endpoints live on the parent viewsets (ObjectViewSet/RouteViewSet);
here are the cross-entity list and owner edit/archive/restore/delete flows.
"""
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import CulturalObjectTranslation, RouteTranslation, TranslationStatus
from ..pagination import SmallPagePagination


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_translations(request):
    """Translation/content proposals submitted by the current user, across objects and routes."""

    def payload(tr, kind, parent, url_prefix):
        return {
            'id': tr.id,
            'kind': kind,
            'target_id': parent.id,
            'target_title': parent.title,
            'target_url': f'/{url_prefix}/{parent.id}',
            'language': tr.language,
            'title': tr.title,
            'status': tr.status,
            'reviewer_note': tr.reviewer_note,
            'created_at': tr.created_at,
            'updated_at': tr.updated_at,
        }

    status_filter = request.query_params.get('status')
    if status_filter not in dict(TranslationStatus.choices):
        status_filter = None

    obj_qs = CulturalObjectTranslation.objects.filter(submitted_by=request.user).select_related('cultural_object')
    route_qs = RouteTranslation.objects.filter(submitted_by=request.user).select_related('route')
    if status_filter:
        obj_qs = obj_qs.filter(status=status_filter)
        route_qs = route_qs.filter(status=status_filter)

    rows = []
    for tr in obj_qs:
        rows.append((tr.created_at, payload(tr, 'object', tr.cultural_object, 'objects')))
    for tr in route_qs:
        rows.append((tr.created_at, payload(tr, 'route', tr.route, 'routes')))

    rows.sort(key=lambda r: r[0], reverse=True)
    items = [r[1] for r in rows]

    paginator = SmallPagePagination()
    page = paginator.paginate_queryset(items, request)
    return paginator.get_paginated_response(page)


def _translation_model_for(kind):
    return {'object': CulturalObjectTranslation, 'route': RouteTranslation}.get(kind)


def _translation_parent(translation, kind):
    return translation.cultural_object if kind == 'object' else translation.route


def _translation_has_replacement(translation, kind):
    """A description must remain visible after hiding an approved translation:
    either the parent's canonical description is non-empty, or another approved translation exists."""
    parent = _translation_parent(translation, kind)
    if (parent.description or '').strip():
        return True
    model = type(translation)
    filter_kw = {'cultural_object': parent} if kind == 'object' else {'route': parent}
    return model.objects.filter(status='approved', **filter_kw).exclude(pk=translation.pk).exists()


def _get_own_translation(request, kind, pk):
    """Return (translation, error_response). error_response is None on success."""
    model = _translation_model_for(kind)
    if model is None:
        return None, Response({'detail': _('Невідомий тип перекладу.')}, status=status.HTTP_404_NOT_FOUND)
    try:
        translation = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return None, Response({'detail': _('Переклад не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
    if translation.submitted_by_id != request.user.id:
        return None, Response({'detail': _('Дозволено лише автору пропозиції.')}, status=status.HTTP_403_FORBIDDEN)
    return translation, None


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def manage_my_translation(request, kind, pk):
    """PATCH = edit own proposal → back to moderation (pending). DELETE = permanent (archived only)."""
    translation, err = _get_own_translation(request, kind, pk)
    if err:
        return err

    if request.method == 'DELETE':
        if translation.status != TranslationStatus.ARCHIVED:
            return Response(
                {'detail': _('Спершу архівуйте переклад, потім його можна видалити назавжди.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        translation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH — edit content, re-submit for moderation.
    if translation.status == TranslationStatus.APPROVED and not _translation_has_replacement(translation, kind):
        return Response(
            {'detail': _('Не можна редагувати: це єдиний опис і не лишиться заміни. Спершу додайте інший переклад.')},
            status=status.HTTP_400_BAD_REQUEST,
        )
    title = request.data.get('title')
    if title is not None:
        translation.title = title[:200]
    if 'description' in request.data:
        translation.description = request.data.get('description') or ''
    translation.status = TranslationStatus.PENDING
    translation.save(update_fields=['title', 'description', 'status', 'updated_at'])
    return Response({'id': translation.id, 'kind': kind, 'status': translation.status})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def archive_my_translation(request, kind, pk):
    """Owner soft-removes their proposal (any status → archived; hidden from public)."""
    translation, err = _get_own_translation(request, kind, pk)
    if err:
        return err
    if translation.status == TranslationStatus.APPROVED and not _translation_has_replacement(translation, kind):
        return Response(
            {'detail': _('Не можна архівувати: це єдиний опис і не лишиться заміни. Спершу додайте інший переклад.')},
            status=status.HTTP_400_BAD_REQUEST,
        )
    translation.status = TranslationStatus.ARCHIVED
    translation.save(update_fields=['status', 'updated_at'])
    return Response({'id': translation.id, 'kind': kind, 'status': translation.status})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def restore_my_translation(request, kind, pk):
    """Owner restores an archived proposal → back to moderation (pending)."""
    translation, err = _get_own_translation(request, kind, pk)
    if err:
        return err
    if translation.status != TranslationStatus.ARCHIVED:
        return Response({'detail': _('Відновити можна лише архівований переклад.')},
                        status=status.HTTP_400_BAD_REQUEST)
    translation.status = TranslationStatus.PENDING
    translation.save(update_fields=['status', 'updated_at'])
    return Response({'id': translation.id, 'kind': kind, 'status': translation.status})
