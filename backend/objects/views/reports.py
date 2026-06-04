"""Polymorphic inaccuracy reports: creation, own-report management, owner lists."""
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import InaccuracyReport
from ..pagination import SmallPagePagination
from ..report_targets import resolve_target
from ..serializers import InaccuracyReportSerializer


def _create_report(request, target_type, target_id):
    """Shared report-creation logic for any content type."""
    instance, cfg = resolve_target(target_type, target_id)
    if instance is None:
        return Response({'detail': _('Контент не знайдено.')}, status=status.HTTP_404_NOT_FOUND)

    ct = ContentType.objects.get_for_model(cfg['model'])

    # Throttle: 1 report per (user, target) per 24h
    recent = InaccuracyReport.objects.filter(
        reporter=request.user,
        content_type=ct,
        object_id=instance.pk,
        created_at__gte=timezone.now() - timedelta(days=1),
    ).exists()
    if recent:
        return Response(
            {'detail': _('Ви вже надсилали репорт на цей контент нещодавно. Спробуйте через 24 години.')},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    reason_type = request.data.get('reason_type')
    if reason_type not in dict(InaccuracyReport.ReasonType.choices):
        return Response({'reason_type': [_('Невірна причина.')]}, status=status.HTTP_400_BAD_REQUEST)

    report = InaccuracyReport.objects.create(
        content_type=ct,
        object_id=instance.pk,
        content_owner_id=cfg['owner_id'](instance),
        reporter=request.user,
        reason_type=reason_type,
        note=request.data.get('note', '')[:2000],
    )
    return Response(
        InaccuracyReportSerializer(report).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_report(request):
    """Generic report endpoint: body {target_type, target_id, reason_type, note}."""
    return _create_report(request, request.data.get('target_type'), request.data.get('target_id'))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_object(request, object_pk):
    """Backward-compatible object-report endpoint."""
    return _create_report(request, 'object', object_pk)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_own_report(request, report_pk):
    try:
        report = InaccuracyReport.objects.get(pk=report_pk)
    except InaccuracyReport.DoesNotExist:
        return Response({'detail': _('Репорт не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
    if report.reporter_id != request.user.id:
        return Response({'detail': _('Не можна видалити чужий репорт.')}, status=status.HTTP_403_FORBIDDEN)
    if report.status != InaccuracyReport.Status.PENDING:
        return Response(
            {'detail': _('Можна видалити лише репорт зі статусом «На розгляді».')},
            status=status.HTTP_400_BAD_REQUEST,
        )
    report.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_reports(request):
    qs = (InaccuracyReport.objects
          .filter(reporter=request.user)
          .select_related('content_type', 'reporter')
          .prefetch_related('target'))
    paginator = SmallPagePagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(InaccuracyReportSerializer(page, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_on_my_objects(request):
    """Reports on any content owned by the current user (objects, routes, photos, audio)."""
    qs = (InaccuracyReport.objects
          .filter(content_owner=request.user)
          .select_related('content_type', 'reporter')
          .prefetch_related('target'))
    paginator = SmallPagePagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(InaccuracyReportSerializer(page, many=True).data)
