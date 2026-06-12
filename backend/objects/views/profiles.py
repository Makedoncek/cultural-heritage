"""Public author profiles, follow toggles and the followed-authors list."""
from django.contrib.auth.models import User
from django.db.models import Count, Exists, OuterRef, Q
from django.utils.translation import gettext as _
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import status, viewsets
from rest_framework import serializers as s
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import CulturalObject, Favorite, FavoriteAuthor
from ..pagination import SmallPagePagination
from ..serializers import ObjectListSerializer, UserProfileSerializer
from ._common import toggle_membership
from .schemas import ErrorResponse


class UserProfileViewSet(viewsets.GenericViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [AllowAny]
    lookup_field = 'username'
    lookup_value_regex = r'[\w.@+-]+'

    def get_queryset(self):
        qs = User.objects.filter(is_active=True).annotate(
            approved_objects_count=Count(
                'cultural_objects',
                filter=Q(cultural_objects__status='approved'),
            ),
            total_favorites_received=Count(
                'cultural_objects__favorited_by',
                filter=Q(cultural_objects__status='approved'),
            ),
            followers_count=Count('followers', distinct=True),
        )
        if self.request.user.is_authenticated:
            qs = qs.annotate(
                is_followed=Exists(
                    FavoriteAuthor.objects.filter(user=self.request.user, author=OuterRef('pk'))
                )
            )
        return qs

    @extend_schema(
        tags=['Users'],
        summary='User profile',
        description='Public profile by username. Use "me" for current user.',
        responses={200: UserProfileSerializer, 404: ErrorResponse},
    )
    def retrieve(self, request, username=None):
        if username == 'me':
            if not request.user.is_authenticated:
                return Response(
                    {'detail': 'Необхідна авторизація.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            username = request.user.username

        try:
            user = self.get_queryset().get(username=username)
        except User.DoesNotExist:
            return Response({'detail': _('Користувача не знайдено.')}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @extend_schema(
        tags=['Users'],
        summary='Author objects',
        description='Approved objects by this author. Own profile also shows pending.',
        responses={200: ObjectListSerializer(many=True), 404: ErrorResponse},
    )
    @action(detail=True, methods=['get'], url_path='objects')
    def objects(self, request, username=None):
        try:
            author = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            return Response({'detail': _('Користувача не знайдено.')}, status=status.HTTP_404_NOT_FOUND)

        qs = (CulturalObject.objects
              .select_related('author')
              .prefetch_related('tags')
              .annotate(favorites_count=Count('favorited_by', distinct=True))
              .filter(author=author)
              .order_by('-created_at'))

        if request.user.is_authenticated:
            qs = qs.annotate(
                _is_favorited=Exists(Favorite.objects.filter(user=request.user, cultural_object=OuterRef('pk')))
            )

        # Own profile: show pending too; others: approved only
        if request.user == author:
            qs = qs.exclude(status='archived')
        else:
            qs = qs.filter(status='approved')

        serializer = ObjectListSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        tags=['Users'],
        summary='Toggle follow',
        description='Follow or unfollow an author.',
        responses={200: inline_serializer('FollowToggle', fields={
            'is_followed': s.BooleanField(),
            'followers_count': s.IntegerField(),
        })},
    )
    @action(detail=True, methods=['post'], url_path='follow', permission_classes=[IsAuthenticated])
    def follow(self, request, username=None):
        try:
            author = User.objects.get(username=username, is_active=True)
        except User.DoesNotExist:
            return Response({'detail': _('Користувача не знайдено.')}, status=status.HTTP_404_NOT_FOUND)

        if request.user == author:
            return Response({'detail': _('Не можна підписатися на себе.')}, status=status.HTTP_400_BAD_REQUEST)

        created, _fav = toggle_membership(FavoriteAuthor, user=request.user, author=author)
        return Response({
            'is_followed': created,
            'followers_count': author.followers.count(),
        })

    @extend_schema(
        tags=['Users'],
        summary='Favorite authors',
        description='Authors followed by the current user.',
        responses={200: UserProfileSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='favorite-authors', permission_classes=[IsAuthenticated])
    def favorite_authors(self, request):
        author_ids = FavoriteAuthor.objects.filter(user=request.user).values_list('author_id', flat=True)
        authors = self.get_queryset().filter(id__in=author_ids)
        paginator = SmallPagePagination()
        page = paginator.paginate_queryset(authors, request, view=self)
        return paginator.get_paginated_response(self.get_serializer(page, many=True).data)
