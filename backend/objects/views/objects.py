"""CulturalObject CRUD with the three-state moderation model
(pending/approved/archived) plus favorites, duplicates check and media lists."""
from django.db.models import Count, Exists, OuterRef, Q, Subquery
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import filters, status, viewsets
from rest_framework import serializers as s
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from ..filters import ObjectFilter
from ..models import (
    CulturalObject, CulturalObjectTranslation, Favorite, ObjectAudio, ObjectPhoto, Visit,
)
from ..pagination import SmallPagePagination
from ..permissions import IsAuthorOrReadOnly
from ..serializers import (
    CulturalObjectTranslationSerializer, ObjectAudioSerializer,
    ObjectDetailSerializer, ObjectListSerializer, ObjectMapSerializer,
    ObjectWithMyPhotosSerializer, ObjectWriteSerializer,
)
from ._common import get_or_404, require_owner_or_staff
from .schemas import OBJECT_VIEWSET_SCHEMA, ErrorResponse


@OBJECT_VIEWSET_SCHEMA
class ObjectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ObjectFilter
    search_fields = ['title', 'description']

    def get_serializer_class(self):
        if self.action == 'list':
            return ObjectListSerializer

        elif self.action in ['create', 'update', 'partial_update']:
            return ObjectWriteSerializer

        return ObjectDetailSerializer

    def get_queryset(self):
        user = self.request.user

        # Subquery для cover_thumbnail_url — щоб уникнути N+1 на @property cover_url
        cover_thumb_sq = ObjectPhoto.objects.filter(
            cultural_object=OuterRef('pk'),
            status='approved',
        ).order_by('-is_author_photo', 'order', 'created_at').values('thumbnail_url')[:1]

        base_qs = (CulturalObject.objects
                   .select_related('author')
                   .prefetch_related('tags', 'translations')
                   .annotate(favorites_count=Count('favorited_by', distinct=True))
                   .annotate(_cover_thumbnail_url=Subquery(cover_thumb_sq))
                   .order_by('-created_at'))

        if user.is_authenticated:
            base_qs = base_qs.annotate(
                _is_favorited=Exists(Favorite.objects.filter(user=user, cultural_object=OuterRef('pk'))),
                # без анотації серіалізатор робить окремий exists-запит на кожен об'єкт (N+1)
                _is_visited=Exists(Visit.objects.filter(user=user, cultural_object=OuterRef('pk'))),
            )

        # Author/admin can retrieve their own archived objects; list/other actions exclude archived.
        if self.action == 'retrieve':
            if user.is_staff:
                return base_qs
            if user.is_authenticated:
                return base_qs.filter(Q(status='approved') | Q(author=user)).distinct().order_by('-created_at')
            return base_qs.filter(status='approved')

        base_qs = base_qs.exclude(status='archived')

        if user.is_staff:
            return base_qs

        if user.is_authenticated:
            return base_qs.filter(Q(status='approved') | Q(author=user)).distinct().order_by('-created_at')

        return base_qs.filter(status='approved')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.instance
        is_approved = instance.status == 'approved'

        if (not self.request.user.is_staff and is_approved
                and self._has_actual_changes(instance, serializer.validated_data)):
            serializer.save(status='pending')
        else:
            serializer.save()

    @staticmethod
    def _has_actual_changes(instance, validated_data):
        """Перевіряє, чи дійсно змінились значення (PATCH тим самим контентом — no-op)."""
        for field, value in validated_data.items():
            if field == 'tags':
                current = set(instance.tags.values_list('id', flat=True))
                new = {t.pk for t in value}
                if current != new:
                    return True
            else:
                if getattr(instance, field, None) != value:
                    return True
        return False

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.archive()
        return Response({'detail': _("Об'єкт архівовано")}, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Полегшений список для карти',
        description='Усі видимі об\'єкти одним запитом без пагінації; '
                    'теги — лише id. Підтримує ті самі фільтри, що й основний список.',
        responses=ObjectMapSerializer(many=True),
    )
    @action(detail=False, methods=['get'])
    def map(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = ObjectMapSerializer(queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def restore(self, request, pk=None):
        """Author or admin restores archived object → status='pending' (requires re-approval)."""
        instance = get_or_404(CulturalObject, pk=pk)
        require_owner_or_staff(request, instance.author_id)
        if instance.status != CulturalObject.Status.ARCHIVED:
            return Response({'detail': _('Об\'єкт не в архіві.')}, status=status.HTTP_400_BAD_REQUEST)
        instance.restore()
        return Response({'detail': _("Об'єкт відновлено")}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='hard-delete', permission_classes=[IsAuthenticated])
    def hard_delete(self, request, pk=None):
        """Author or admin permanently deletes object (regardless of status)."""
        instance = get_or_404(CulturalObject, pk=pk)
        require_owner_or_staff(request, instance.author_id)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], url_path='check-duplicates', permission_classes=[AllowAny])
    def check_duplicates(self, request):
        """Returns approved objects within 100 m of the given coordinates.

        Used by the create-object form as a soft duplicate warning: client
        shows the list, user decides whether to proceed or pick an existing one.
        Read-only — does not create or modify anything.
        """
        from ..services.geo import find_nearby_objects
        try:
            latitude = float(request.data.get('latitude'))
            longitude = float(request.data.get('longitude'))
        except (TypeError, ValueError):
            return Response({'detail': _('latitude і longitude обовʼязкові')},
                            status=status.HTTP_400_BAD_REQUEST)
        exclude_id = request.data.get('exclude_id')
        try:
            exclude_id = int(exclude_id) if exclude_id is not None else None
        except (TypeError, ValueError):
            exclude_id = None
        nearby = find_nearby_objects(latitude, longitude, radius_m=100.0, exclude_id=exclude_id)
        return Response({
            'nearby': [
                {
                    'id': obj.id,
                    'title': obj.title,
                    'latitude': str(obj.latitude),
                    'longitude': str(obj.longitude),
                    'distance_m': round(distance, 1),
                }
                for obj, distance in nearby[:5]
            ],
        })

    @extend_schema(
        tags=['Objects'],
        summary='My objects',
        description='List of current user\'s objects (excluding archived). Requires authentication.',
        responses={200: ObjectListSerializer(many=True), 401: ErrorResponse},
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my(self, request):
        objects = (CulturalObject.objects
                   .select_related('author')
                   .prefetch_related('tags')
                   .filter(author=request.user)
                   .order_by('-created_at'))
        paginator = SmallPagePagination()
        page = paginator.paginate_queryset(objects, request, view=self)
        serializer = ObjectListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'], url_path='translations', permission_classes=[IsAuthenticated])
    def submit_translation(self, request, pk=None):
        """Submit a community translation for this object (status='pending'; admin moderates via Django Admin)."""
        obj = get_or_404(CulturalObject, pk=pk)
        serializer = CulturalObjectTranslationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        lang = serializer.validated_data['language']
        # Proposals are allowed for any language, including the original — an approved
        # original-language proposal is applied to the canonical content by the admin.
        # Multiple competing pending proposals per language are allowed.
        translation = CulturalObjectTranslation.objects.create(
            cultural_object=obj,
            language=lang,
            title=serializer.validated_data['title'],
            description=serializer.validated_data.get('description', ''),
            submitted_by=request.user,
        )
        return Response(
            CulturalObjectTranslationSerializer(translation).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=['Objects'],
        summary='Objects where I uploaded photos',
        description='Returns objects (own or others) where the current user has uploaded at least one photo. Each item includes a `my_photos` array with statuses.',
        responses={200: ObjectWithMyPhotosSerializer(many=True), 401: ErrorResponse},
    )
    @action(detail=False, methods=['get'], url_path='with-my-photos', permission_classes=[IsAuthenticated])
    def with_my_photos(self, request):
        status_filter = request.query_params.get('status')
        my_photos = ObjectPhoto.objects.filter(uploaded_by=request.user)
        if status_filter in dict(ObjectPhoto.Status.choices):
            my_photos = my_photos.filter(status=status_filter)
        else:
            status_filter = None
        object_ids = my_photos.values_list('cultural_object_id', flat=True).distinct()

        objects = (CulturalObject.objects
                   .select_related('author')
                   .prefetch_related('tags', 'photos__uploaded_by')
                   .filter(id__in=object_ids)
                   .exclude(status='archived')
                   .order_by('-created_at'))

        paginator = SmallPagePagination()
        page = paginator.paginate_queryset(objects, request, view=self)
        serializer = ObjectWithMyPhotosSerializer(
            page, many=True, context={'request': request, 'photo_status': status_filter},
        )
        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'], url_path='with-my-audios', permission_classes=[IsAuthenticated])
    def with_my_audios(self, request):
        """Objects (any author) where the current user has uploaded at least one audio narrative."""
        status_filter = request.query_params.get('status')
        my_audios_qs = ObjectAudio.objects.filter(uploaded_by=request.user)
        if status_filter in dict(ObjectAudio.Status.choices):
            my_audios_qs = my_audios_qs.filter(status=status_filter)
        else:
            status_filter = None
        object_ids = my_audios_qs.values_list('cultural_object_id', flat=True).distinct()
        objects = (CulturalObject.objects
                   .select_related('author')
                   .prefetch_related('tags')
                   .filter(id__in=object_ids)
                   .exclude(status='archived')
                   .order_by('-created_at'))

        def serialize(obj):
            audios = obj.audios.filter(uploaded_by=request.user)
            if status_filter:
                audios = audios.filter(status=status_filter)
            my_audios = list(audios.order_by('-created_at'))
            return {
                'id': obj.id,
                'title': obj.title,
                'tags': [{'id': tg.id, 'name': tg.name, 'icon': tg.icon} for tg in obj.tags.all()],
                'author_name': obj.author.username,
                'my_audios': ObjectAudioSerializer(my_audios, many=True).data,
            }

        paginator = SmallPagePagination()
        page = paginator.paginate_queryset(objects, request, view=self)
        return paginator.get_paginated_response([serialize(o) for o in page])

    @extend_schema(
        tags=['Objects'],
        summary='Toggle favorite',
        description='Add or remove object from favorites. Returns new state.',
        responses={200: inline_serializer('FavoriteToggle', fields={
            'is_favorited': s.BooleanField(),
            'favorites_count': s.IntegerField(),
        })},
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        obj = self.get_object()
        if obj.author_id == request.user.id:
            return Response(
                {'detail': _('Не можна додати власний об\'єкт до обраного.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fav, created = Favorite.objects.get_or_create(user=request.user, cultural_object=obj)
        if not created:
            fav.delete()
        return Response({
            'is_favorited': created,
            'favorites_count': obj.favorited_by.count(),
        })

    @extend_schema(
        tags=['Objects'],
        summary='List favorites',
        description='Returns objects favorited by the current user.',
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def favorites(self, request):
        favorite_ids = Favorite.objects.filter(user=request.user).values_list('cultural_object_id', flat=True)
        objects = self.get_queryset().filter(id__in=favorite_ids).order_by('-created_at')
        paginator = SmallPagePagination()
        page = paginator.paginate_queryset(objects, request, view=self)
        return paginator.get_paginated_response(
            ObjectListSerializer(page, many=True, context={'request': request}).data,
        )

    @extend_schema(
        tags=['Objects'],
        summary='Popular objects',
        description='Returns top objects sorted by favorites count. Public endpoint.',
    )
    @action(detail=False, methods=['get'])
    def popular(self, request):
        objects = (self.get_queryset()
                   .filter(status='approved', favorites_count__gt=0)
                   .order_by('-favorites_count', '-created_at')[:20])

        serializer = ObjectListSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)
