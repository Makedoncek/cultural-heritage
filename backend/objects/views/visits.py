"""Visits ('I was here') and planned visits — the cultural passport feature."""
from django.contrib.auth.models import User
from django.db.models import Count, F, Q
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import CulturalObject, PlannedVisit, Route, Tag, Visit
from ..pagination import SmallPagePagination
from ..serializers import PlannedVisitSerializer, VisitMapPointSerializer, VisitSerializer
from ._common import toggle_membership


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_visit(request, object_pk):
    """Toggle 'I visited' for the current user."""
    try:
        obj = CulturalObject.objects.get(pk=object_pk)
    except CulturalObject.DoesNotExist:
        return Response({'detail': _('Об\'єкт не знайдено.')}, status=status.HTTP_404_NOT_FOUND)

    created, visit = toggle_membership(Visit, user=request.user, cultural_object=obj)
    if not created:
        return Response({'is_visited': False})
    return Response({'is_visited': True, 'visit': VisitSerializer(visit).data}, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_visit(request, visit_pk):
    """Edit own visit: impression, visited_at, is_public."""
    try:
        visit = Visit.objects.get(pk=visit_pk)
    except Visit.DoesNotExist:
        return Response({'detail': _('Візит не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
    if visit.user_id != request.user.id:
        return Response({'detail': _('Не можна редагувати чужий візит.')}, status=status.HTTP_403_FORBIDDEN)

    allowed = {'impression', 'visited_at', 'is_public'}
    updates = {k: v for k, v in request.data.items() if k in allowed}

    if 'visited_at' in updates:
        from datetime import datetime
        raw = str(updates['visited_at'])
        try:
            # Accept full ISO datetime or legacy date-only ('YYYY-MM-DD' → midnight local).
            parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        except ValueError:
            return Response({'visited_at': [_('Невірний формат дати/часу.')]}, status=status.HTTP_400_BAD_REQUEST)
        if parsed.tzinfo is None:
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        if parsed > timezone.now():
            return Response(
                {'visited_at': [_('Дата візиту не може бути у майбутньому.')]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updates['visited_at'] = parsed

    for k, v in updates.items():
        setattr(visit, k, v)
    visit.save()
    return Response(VisitSerializer(visit).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def visits_count(request, object_pk):
    """Public: how many unique users visited this object."""
    count = Visit.objects.filter(cultural_object_id=object_pk).count()
    return Response({'visits_count': count})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_visits(request):
    qs = Visit.objects.filter(user=request.user).select_related('cultural_object')
    paginator = SmallPagePagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(VisitSerializer(page, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_visits(request, username):
    try:
        target = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'detail': _('Користувача не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
    qs = Visit.objects.filter(user=target, is_public=True).select_related('cultural_object')
    paginator = SmallPagePagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(VisitSerializer(page, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_visits_map(request, username):
    """All public visits of a user as lightweight map points (unpaginated — the map shows everything)."""
    try:
        target = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'detail': _('Користувача не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
    qs = Visit.objects.filter(user=target, is_public=True).select_related('cultural_object')
    return Response(VisitMapPointSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_visits_stats(request):
    """Aggregated counts for the cultural passport dashboard."""
    base = Visit.objects.filter(user=request.user)
    total = base.count()
    total_objects = CulturalObject.objects.filter(status='approved').count()
    by_tag = list(
        Tag.objects.filter(cultural_objects__visits__user=request.user)
        .annotate(visited_count=Count('cultural_objects__visits',
                                      filter=Q(cultural_objects__visits__user=request.user),
                                      distinct=True))
        .values('id', 'name', 'icon', 'visited_count')
        .order_by('-visited_count')
    )
    # Routes counted as completed when every stop's object has a Visit by the user.
    completed_routes = (
        Route.objects.filter(stops__isnull=False)
        .annotate(
            total_stops=Count('stops', distinct=True),
            visited_stops=Count(
                'stops',
                filter=Q(stops__cultural_object__visits__user=request.user),
                distinct=True,
            ),
        )
        .filter(total_stops__gt=0, visited_stops=F('total_stops'))
        .count()
    )
    return Response({
        'total_visits': total,
        'total_approved_objects': total_objects,
        'completed_routes': completed_routes,
        'by_tag': by_tag,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_planned_visit(request, object_pk):
    """Toggle 'I plan to visit' for the current user."""
    try:
        obj = CulturalObject.objects.get(pk=object_pk)
    except CulturalObject.DoesNotExist:
        return Response({'detail': _('Об\'єкт не знайдено.')}, status=status.HTTP_404_NOT_FOUND)

    created, planned = toggle_membership(PlannedVisit, user=request.user, cultural_object=obj)
    if not created:
        return Response({'is_planned': False})
    return Response(
        {'is_planned': True, 'planned': PlannedVisitSerializer(planned).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_planned_visit(request, planned_pk):
    try:
        planned = PlannedVisit.objects.get(pk=planned_pk)
    except PlannedVisit.DoesNotExist:
        return Response({'detail': _('План не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
    if planned.user_id != request.user.id:
        return Response({'detail': _('Не можна редагувати чужий план.')}, status=status.HTTP_403_FORBIDDEN)

    allowed = {'planned_date', 'note'}
    for k, v in request.data.items():
        if k in allowed:
            setattr(planned, k, v)
    planned.save()
    return Response(PlannedVisitSerializer(planned).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def convert_planned_to_visit(request, planned_pk):
    """Convert a PlannedVisit into a Visit (deletes plan, creates visit)."""
    try:
        planned = PlannedVisit.objects.get(pk=planned_pk)
    except PlannedVisit.DoesNotExist:
        return Response({'detail': _('План не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
    if planned.user_id != request.user.id:
        return Response({'detail': _('Не можна конвертувати чужий план.')}, status=status.HTTP_403_FORBIDDEN)

    visit, created = Visit.objects.get_or_create(
        user=planned.user,
        cultural_object=planned.cultural_object,
        defaults={'impression': planned.note},
    )
    planned.delete()
    return Response(
        {'visit': VisitSerializer(visit).data, 'created': created},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_planned_visits(request):
    qs = PlannedVisit.objects.filter(user=request.user).select_related('cultural_object')
    paginator = SmallPagePagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(PlannedVisitSerializer(page, many=True).data)
