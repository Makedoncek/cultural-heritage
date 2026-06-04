"""Heritage Routes: CRUD, stops management, ORS geometry/optimization, export."""
from django.db.models import Count, F, Max, Q
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import (
    CulturalObject, Route, RouteStop, RouteTranslation, Visit,
)
from ..pagination import SmallPagePagination
from ..serializers import (
    RouteDetailSerializer, RouteListSerializer, RouteStopSerializer,
    RouteTranslationSerializer, RouteWriteSerializer,
)
from ._common import get_or_404, require_owner_or_staff

MAX_STOPS_PER_ROUTE = 50

EDIT_FOREIGN_MSG = 'Не можна редагувати чужий маршрут.'


def _enrich_ors_error(message: str, stops: list) -> str:
    """Add stop titles to ORS error messages that only reference coordinates.

    ORS errors mention points either as `coordinate N: lng lat`, `points N (lng lat) and M (lng lat)`,
    or `location [lng,lat]`. We re-emit the same text with the matching stop's title attached so
    the user can identify which object on the map is causing the problem.
    """
    import re

    def stop_label(lng: float, lat: float) -> str:
        # Match coordinates to stops with 1e-3 tolerance (~100m) — handles ORS rounding.
        for stop in stops:
            obj_lng = float(stop.cultural_object.longitude)
            obj_lat = float(stop.cultural_object.latitude)
            if abs(obj_lng - lng) < 1e-3 and abs(obj_lat - lat) < 1e-3:
                return f'«{stop.cultural_object.title}»'
        return ''

    # Pattern A: "coordinate 0: 33.7894950 51.5395490"
    def fix_coord(m: re.Match) -> str:
        idx, lng, lat = m.group(1), float(m.group(2)), float(m.group(3))
        title = stop_label(lng, lat)
        return f'coordinate {idx} {title} ({lng}, {lat})' if title else m.group(0)

    message = re.sub(r'coordinate (\d+):\s*([\d.\-]+)\s+([\d.\-]+)', fix_coord, message)

    # Pattern B: "points 3 (31.7680290 49.5359790) and 4 (30.2706490 51.3600520)"
    def fix_pair(m: re.Match) -> str:
        a, a_lng, a_lat = m.group(1), float(m.group(2)), float(m.group(3))
        b, b_lng, b_lat = m.group(4), float(m.group(5)), float(m.group(6))
        ta, tb = stop_label(a_lng, a_lat), stop_label(b_lng, b_lat)
        sa = f'{a} {ta}' if ta else f'{a} ({a_lng}, {a_lat})'
        sb = f'{b} {tb}' if tb else f'{b} ({b_lng}, {b_lat})'
        return f'points {sa} and {sb}'

    message = re.sub(
        r'points (\d+) \(([\d.\-]+)\s+([\d.\-]+)\) and (\d+) \(([\d.\-]+)\s+([\d.\-]+)\)',
        fix_pair, message,
    )

    # Pattern C: "location [30.270649,51.360052]" (vroom)
    def fix_location(m: re.Match) -> str:
        lng, lat = float(m.group(1)), float(m.group(2))
        title = stop_label(lng, lat)
        return f'location {title} [{lng}, {lat}]' if title else m.group(0)

    message = re.sub(r'location \[([\d.\-]+),([\d.\-]+)\]', fix_location, message)

    return message


class RouteViewSet(viewsets.ModelViewSet):
    """CRUD for Heritage Routes.

    Visibility:
      - public list: only approved routes
      - draft/pending visible to author + admin
    """

    # Default lookup_field='pk' — routes are identified by numeric ID.

    def get_serializer_class(self):
        if self.action == 'list':
            return RouteListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return RouteWriteSerializer
        return RouteDetailSerializer

    def get_queryset(self):
        qs = Route.objects.select_related('author').prefetch_related(
            'tags', 'stops__cultural_object', 'stops__cultural_object__translations', 'translations',
        )
        if self.action == 'list':
            return self._filter_list_queryset(qs)
        if self.action == 'retrieve':
            return self._filter_retrieve_queryset(qs)
        return qs

    def _filter_list_queryset(self, qs):
        # Public catalog: only public routes that have been approved.
        qs = qs.filter(visibility=Route.Visibility.PUBLIC, status=Route.Status.APPROVED)
        params = self.request.query_params
        if params.get('is_featured') == 'true':
            qs = qs.filter(is_featured=True)
        tag_ids = params.get('tags')
        if tag_ids:
            ids = [int(t) for t in tag_ids.split(',') if t.isdigit()]
            if ids:
                qs = qs.filter(tags__id__in=ids).distinct()
        search = (params.get('search') or '').strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))
        # Duration filter (minutes). Treats null estimated_duration_minutes as 0.
        dmin = params.get('duration_min')
        dmax = params.get('duration_max')
        if dmin and dmin.isdigit():
            qs = qs.filter(estimated_duration_minutes__gte=int(dmin))
        if dmax and dmax.isdigit():
            qs = qs.filter(estimated_duration_minutes__lte=int(dmax))
        return qs

    def _filter_retrieve_queryset(self, qs):
        user = self.request.user
        if not user.is_authenticated:
            return qs.filter(visibility=Route.Visibility.PUBLIC, status=Route.Status.APPROVED)
        if user.is_staff:
            return qs
        # Author sees own routes (any visibility); others only public+approved.
        return qs.filter(
            Q(author=user) |
            Q(visibility=Route.Visibility.PUBLIC, status=Route.Status.APPROVED)
        )

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy',
                           'submit', 'copy', 'add_stop', 'reorder', 'stop_detail'):
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # Pre-fetch which stops the current user has already visited (one query per route).
        user = self.request.user if hasattr(self.request, 'user') else None
        if self.action == 'retrieve' and user and user.is_authenticated:
            route_id = self.kwargs.get('pk')
            if route_id:
                stop_object_ids = list(
                    RouteStop.objects.filter(route_id=route_id).values_list('cultural_object_id', flat=True),
                )
                visited_ids = set(
                    Visit.objects.filter(user=user, cultural_object_id__in=stop_object_ids)
                    .values_list('cultural_object_id', flat=True),
                )
                context['visited_object_ids'] = visited_ids
        return context

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, status=Route.Status.DRAFT)

    def create(self, request, *args, **kwargs):
        # Use write serializer for validation, detail serializer for the response
        # so the frontend immediately gets `id`, `status`, etc.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            RouteDetailSerializer(serializer.instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        require_owner_or_staff(request, instance.author_id, EDIT_FOREIGN_MSG)
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        # If user switches private→public, send the route back to draft so it goes through moderation.
        new_visibility = serializer.validated_data.get('visibility')
        if (new_visibility == Route.Visibility.PUBLIC
                and instance.visibility == Route.Visibility.PRIVATE):
            serializer.validated_data['status'] = Route.Status.DRAFT
        self.perform_update(serializer)
        return Response(
            RouteDetailSerializer(serializer.instance, context={'request': request}).data,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        require_owner_or_staff(request, instance.author_id, 'Не можна видалити чужий маршрут.')
        instance.status = Route.Status.ARCHIVED
        instance.save(update_fields=['status', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Author or admin restores archived route → status='draft'."""
        instance = get_or_404(Route, pk=pk)
        require_owner_or_staff(request, instance.author_id)
        if instance.status != Route.Status.ARCHIVED:
            return Response({'detail': _('Маршрут не в архіві.')}, status=status.HTTP_400_BAD_REQUEST)
        instance.status = Route.Status.DRAFT
        instance.save(update_fields=['status', 'updated_at'])
        return Response(RouteDetailSerializer(instance, context={'request': request}).data)

    @action(detail=True, methods=['delete'], url_path='hard-delete')
    def hard_delete(self, request, pk=None):
        """Author or admin permanently deletes route (regardless of status)."""
        instance = get_or_404(Route, pk=pk)
        require_owner_or_staff(request, instance.author_id)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        route = self.get_object()
        if route.author_id != request.user.id:
            return Response({'detail': _('Тільки автор може подати маршрут на модерацію.')},
                            status=status.HTTP_403_FORBIDDEN)
        if route.visibility != Route.Visibility.PUBLIC:
            return Response(
                {'detail': _('Особистий маршрут не потребує модерації. Зробіть його публічним, щоб подати.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if route.status != Route.Status.DRAFT:
            return Response({'detail': _('Подати на модерацію можна лише чернетку.')},
                            status=status.HTTP_400_BAD_REQUEST)
        if route.stops.count() < 2:
            return Response({'detail': _('Маршрут має містити щонайменше 2 зупинки.')},
                            status=status.HTTP_400_BAD_REQUEST)
        route.status = Route.Status.PENDING
        route.save(update_fields=['status', 'updated_at'])
        return Response(RouteDetailSerializer(route, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def copy(self, request, pk=None):
        original = self.get_object()
        # Can copy only public+approved routes (private ones aren't shareable by design).
        if original.visibility != Route.Visibility.PUBLIC or original.status != Route.Status.APPROVED:
            return Response({'detail': _('Можна копіювати тільки опубліковані маршрути.')},
                            status=status.HTTP_403_FORBIDDEN)
        copy = Route.objects.create(
            title=f'{original.title} (копія)',
            description=original.description,
            author=request.user,
            # Copy defaults to PRIVATE — user explicitly opts in to publish.
            visibility=Route.Visibility.PRIVATE,
            status=Route.Status.DRAFT,
            estimated_duration_minutes=original.estimated_duration_minutes,
            copied_from=original,
        )
        copy.tags.set(original.tags.all())
        for stop in original.stops.all():
            RouteStop.objects.create(
                route=copy,
                cultural_object=stop.cultural_object,
                order=stop.order,
                note=stop.note,
            )
        return Response(
            RouteDetailSerializer(copy, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='stops')
    def add_stop(self, request, pk=None):
        route = self.get_object()
        require_owner_or_staff(request, route.author_id, EDIT_FOREIGN_MSG)
        if route.stops.count() >= MAX_STOPS_PER_ROUTE:
            return Response(
                {'detail': _('Маршрут не може містити більше 50 зупинок.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        object_id = request.data.get('cultural_object')
        try:
            cultural_object = CulturalObject.objects.get(pk=object_id)
        except CulturalObject.DoesNotExist:
            return Response({'cultural_object': [_('Об\'єкт не знайдено.')]},
                            status=status.HTTP_400_BAD_REQUEST)
        if RouteStop.objects.filter(route=route, cultural_object=cultural_object).exists():
            return Response(
                {'detail': _('Цей об\'єкт уже доданий у маршрут.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Use max(order)+1 instead of count()+1 to avoid duplicate `order` when
        # legacy data has gaps (e.g. an old delete that didn't recompact).
        last_order = route.stops.aggregate(m=Max('order'))['m'] or 0
        stop = RouteStop.objects.create(
            route=route,
            cultural_object=cultural_object,
            order=last_order + 1,
            note=str(request.data.get('note', ''))[:500],
        )
        return Response(RouteStopSerializer(stop).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reorder')
    def reorder(self, request, pk=None):
        route = self.get_object()
        require_owner_or_staff(request, route.author_id, EDIT_FOREIGN_MSG)
        items = request.data.get('order') or []
        if not isinstance(items, list):
            return Response({'detail': 'order must be a list'}, status=400)
        ids = [int(it.get('id')) for it in items if 'id' in it and 'order' in it]
        stops = list(RouteStop.objects.filter(route=route, id__in=ids))
        if len(stops) != len(ids):
            return Response({'detail': _('Деякі зупинки не належать цьому маршруту.')},
                            status=status.HTTP_400_BAD_REQUEST)
        by_id = {s.id: s for s in stops}
        for it in items:
            s = by_id[int(it['id'])]
            s.order = int(it['order'])
        RouteStop.objects.bulk_update(stops, ['order'])
        return Response({'detail': 'ok'})

    @action(detail=True, methods=['patch', 'delete'], url_path=r'stops/(?P<stop_pk>\d+)')
    def stop_detail(self, request, pk=None, stop_pk=None):
        """PATCH updates RouteStop (note), DELETE removes it. Author or admin only."""
        route = self.get_object()
        require_owner_or_staff(request, route.author_id, EDIT_FOREIGN_MSG)
        try:
            stop = RouteStop.objects.get(pk=stop_pk, route=route)
        except RouteStop.DoesNotExist:
            return Response({'detail': _('Зупинку не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
        if request.method == 'DELETE':
            stop.delete()
            # Recompact: keep stop orders sequential 1..N (no gaps after delete).
            remaining = list(RouteStop.objects.filter(route=route).order_by('order'))
            for idx, s in enumerate(remaining, start=1):
                if s.order != idx:
                    s.order = idx
            RouteStop.objects.bulk_update(remaining, ['order'])
            return Response(status=status.HTTP_204_NO_CONTENT)
        # PATCH
        if 'note' in request.data:
            stop.note = str(request.data['note'])[:500]
            stop.save(update_fields=['note'])
        return Response(RouteStopSerializer(stop).data)

    @action(detail=True, methods=['post'], url_path='compute-geometry', permission_classes=[IsAuthenticated])
    def compute_geometry(self, request, pk=None):
        """Recompute real-road geometry for the route via OpenRouteService.

        Stores polyline + distance + duration on the Route — frontend then draws
        the cached version (no per-load API calls).
        """
        from ..services.ors import get_directions, ORSError
        route = self.get_object()
        require_owner_or_staff(request, route.author_id)
        stops = list(route.stops.order_by('order'))
        if len(stops) < 2:
            return Response({'detail': _('Маршрут має містити щонайменше 2 зупинки.')},
                            status=status.HTTP_400_BAD_REQUEST)
        coords = [(float(s.cultural_object.longitude), float(s.cultural_object.latitude)) for s in stops]
        profile = request.data.get('profile') or 'foot-walking'
        try:
            result = get_directions(coords, profile=profile)
        except ORSError as exc:
            return Response({'detail': _enrich_ors_error(str(exc), stops)},
                            status=status.HTTP_502_BAD_GATEWAY)
        route.route_geometry = result['geometry']
        route.route_distance_m = result['distance_m']
        route.route_duration_s = result['duration_s']
        route.geometry_updated_at = timezone.now()
        route.save(update_fields=['route_geometry', 'route_distance_m',
                                  'route_duration_s', 'geometry_updated_at', 'updated_at'])
        return Response({
            'geometry': result['geometry'],
            'distance_m': result['distance_m'],
            'duration_s': result['duration_s'],
        })

    @action(detail=True, methods=['post'], url_path='optimize-order', permission_classes=[IsAuthenticated])
    def optimize_order(self, request, pk=None):
        """Reorder stops via ORS Optimization (vroom engine TSP-like solver)."""
        from ..services.ors import get_directions, optimize_order as ors_optimize, ORSError
        route = self.get_object()
        require_owner_or_staff(request, route.author_id)
        stops = list(route.stops.order_by('order'))
        if len(stops) < 3:
            return Response({'detail': _('Для оптимізації потрібно мінімум 3 зупинки.')},
                            status=status.HTTP_400_BAD_REQUEST)
        coords = [(float(s.cultural_object.longitude), float(s.cultural_object.latitude)) for s in stops]
        profile = request.data.get('profile') or 'foot-walking'
        try:
            new_indices = ors_optimize(coords, profile=profile)
        except ORSError as exc:
            return Response({'detail': _enrich_ors_error(str(exc), stops)},
                            status=status.HTTP_502_BAD_GATEWAY)
        # Apply the new order: reorder existing RouteStop rows by their indices.
        reordered_stops = [stops[i] for i in new_indices]
        for new_pos, stop in enumerate(reordered_stops, start=1):
            stop.order = new_pos
        RouteStop.objects.bulk_update(reordered_stops, ['order'])
        # Refresh cached geometry along the new order (best-effort — non-fatal).
        new_coords = [coords[i] for i in new_indices]
        try:
            geo = get_directions(new_coords, profile=profile)
            route.route_geometry = geo['geometry']
            route.route_distance_m = geo['distance_m']
            route.route_duration_s = geo['duration_s']
            route.geometry_updated_at = timezone.now()
        except ORSError:
            route.route_geometry = None
            route.route_distance_m = None
            route.route_duration_s = None
            route.geometry_updated_at = None
        route.save(update_fields=['route_geometry', 'route_distance_m',
                                  'route_duration_s', 'geometry_updated_at', 'updated_at'])
        return Response({
            'new_order': new_indices,
            'stops_count': len(reordered_stops),
            'distance_m': route.route_distance_m,
            'duration_s': route.route_duration_s,
        })

    @action(detail=True, methods=['post'], url_path='mark-completed', permission_classes=[IsAuthenticated])
    def mark_completed(self, request, pk=None):
        """Bulk-create Visits for every stop the user has not yet visited.

        After this call, all stops belong to user.visits -> the route counts as 'completed'
        when stats are computed (no separate RouteCompletion table — derived from Visit data).
        """
        route = self.get_object()
        already_visited = set(
            Visit.objects.filter(user=request.user, cultural_object__in=route.stops.values('cultural_object'))
            .values_list('cultural_object_id', flat=True)
        )
        missing = [s.cultural_object_id for s in route.stops.all() if s.cultural_object_id not in already_visited]
        created = 0
        for object_id in missing:
            Visit.objects.create(
                user=request.user,
                cultural_object_id=object_id,
                visited_at=timezone.now(),
                impression='',
            )
            created += 1
        return Response({'created_visits': created, 'total_stops': route.stops.count()})

    @action(detail=True, methods=['post'], url_path='translations', permission_classes=[IsAuthenticated])
    def submit_translation(self, request, pk=None):
        """Submit a community translation for this route (status='pending'; admin moderates via Django Admin)."""
        route = self.get_object()
        serializer = RouteTranslationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lang = serializer.validated_data['language']
        # Proposals are allowed for any language, including the original — an approved
        # original-language proposal is applied to the canonical content by the admin.
        # Multiple competing pending proposals per language are allowed.
        translation = RouteTranslation.objects.create(
            route=route,
            language=lang,
            title=serializer.validated_data['title'],
            description=serializer.validated_data.get('description', ''),
            submitted_by=request.user,
        )
        return Response(
            RouteTranslationSerializer(translation).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='export')
    def export(self, request, pk=None):
        from ..services.route_export import (
            export_route_as_gpx, export_route_as_kml, export_route_as_kmz,
        )
        from django.http import HttpResponse
        route = self.get_object()
        fmt = request.query_params.get('fmt', 'gpx').lower()
        # Use the requesting browser's origin so dev/staging deploys produce links
        # pointing back at the same host (e.g. http://localhost:5173) rather than the
        # hardcoded production FRONTEND_BASE_URL.
        base_url = request.headers.get('Origin') or \
            request.META.get('HTTP_REFERER', '').rstrip('/').split('/objects')[0].split('/routes')[0] or None
        if fmt == 'gpx':
            content = export_route_as_gpx(route, base_url=base_url)
            content_type = 'application/gpx+xml'
            ext = 'gpx'
        elif fmt == 'kml':
            content = export_route_as_kml(route, base_url=base_url)
            content_type = 'application/vnd.google-earth.kml+xml'
            ext = 'kml'
        elif fmt == 'kmz':
            content = export_route_as_kmz(route, base_url=base_url)
            content_type = 'application/vnd.google-earth.kmz'
            ext = 'kmz'
        else:
            return Response({'detail': _('Підтримувані формати: gpx, kml, kmz.')},
                            status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse(content, content_type=content_type)
        from django.utils.text import slugify
        from urllib.parse import quote
        # Preserve Cyrillic in filename via RFC 6266 — modern browsers honor `filename*`
        # (UTF-8 percent-encoded), older ones fall back to the ASCII-safe `filename` token.
        unicode_name = slugify(route.title, allow_unicode=True) or f'route-{route.pk}'
        ascii_name = slugify(route.title) or f'route-{route.pk}'
        encoded = quote(f'{unicode_name}.{ext}')
        response['Content-Disposition'] = (
            f"attachment; filename=\"{ascii_name}.{ext}\"; filename*=UTF-8''{encoded}"
        )
        return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_routes(request):
    """List routes authored by the current user (any status)."""
    qs = (Route.objects.filter(author=request.user)
          .select_related('author').prefetch_related('tags')
          .order_by('-updated_at'))
    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)
    paginator = SmallPagePagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(
        RouteListSerializer(page, many=True, context={'request': request}).data,
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_completed_routes(request):
    """List routes where the current user has a Visit for every stop."""
    qs = (Route.objects.filter(stops__isnull=False)
          .select_related('author').prefetch_related('tags')
          .annotate(
              total_stops=Count('stops', distinct=True),
              visited_stops=Count(
                  'stops',
                  filter=Q(stops__cultural_object__visits__user=request.user),
                  distinct=True,
              ),
          )
          .filter(total_stops__gt=0, visited_stops=F('total_stops'))
          .order_by('-updated_at'))
    paginator = SmallPagePagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(
        RouteListSerializer(page, many=True, context={'request': request}).data,
    )
