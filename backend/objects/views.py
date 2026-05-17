from rest_framework import status, viewsets, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils.translation import gettext as _
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, inline_serializer
from rest_framework import serializers as s
from .filters import ObjectFilter
from .serializers import RegisterSerializer, TagSerializer, CustomTokenObtainPairSerializer
from .email import send_verification_email, send_password_reset_email, verify_email_token, verify_password_reset_token
from .models import Tag
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Exists, OuterRef, Subquery
from .models import CulturalObject, Favorite, FavoriteAuthor
from .serializers import ObjectListSerializer, ObjectDetailSerializer, ObjectWriteSerializer, UserProfileSerializer, ObjectWithMyPhotosSerializer


class _PhotoLimitExceeded(Exception):
    """Внутрішня помилка для скасування транзакції upload-у при перевищенні ліміту."""
    def __init__(self, code: str, limit: int):
        self.code = code
        self.limit = limit
from .permissions import IsAuthorOrReadOnly, IsPhotoUploaderOrAdmin, IsObjectAuthor, IsPhotoCaptionEditor
from .throttles import PhotoUploadThrottle
from .validators import validate_image_size, validate_image_format
from . import cloudinary_service
from .models import ObjectPhoto
from .serializers import ObjectPhotoSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q

ErrorResponse = inline_serializer('ErrorResponse', fields={'detail': s.CharField()})


@extend_schema(
    tags=['Authentication'],
    summary='Register a new user',
    description='Creates a new user account (inactive) and sends a verification email.',
    request=RegisterSerializer,
    responses={
        201: inline_serializer('RegisterSuccess', fields={
            'message': s.CharField(),
        }),
        400: inline_serializer('RegisterError', fields={
            'username': s.ListField(child=s.CharField(), required=False),
            'email': s.ListField(child=s.CharField(), required=False),
            'password': s.ListField(child=s.CharField(), required=False),
            'password2': s.ListField(child=s.CharField(), required=False),
        }),
    },
    examples=[
        OpenApiExample(
            'Request',
            value={'username': 'alecs7turbo', 'email': 'alecs7turbo@example.com', 'password': 'SecurePass123!',
                   'password2': 'SecurePass123!'},
            request_only=True,
        ),
        OpenApiExample(
            'Success response',
            value={'message': 'Реєстрація успішна! Перевірте вашу електронну пошту для підтвердження.'},
            response_only=True,
            status_codes=['201'],
        ),
        OpenApiExample(
            'Validation error',
            value={
                'username': ['A user with that username already exists.'],
                'password2': ['Passwords do not match.'],
            },
            response_only=True,
            status_codes=['400'],
        ),
    ],
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        send_verification_email.delay(user.id)

        return Response({
            'message': _('Реєстрація успішна! Перевірте вашу електронну пошту для підтвердження.'),
        }, status=status.HTTP_201_CREATED)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@extend_schema(
    tags=['Authentication'],
    summary='Verify email address',
    description='Activates user account via token from verification email.',
    parameters=[OpenApiParameter(name='token', type=str, location=OpenApiParameter.QUERY, required=True)],
    responses={
        200: inline_serializer('VerifyEmailSuccess', fields={'message': s.CharField()}),
        400: inline_serializer('VerifyEmailError', fields={'error': s.CharField()}),
    },
)
@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request):
    token = request.query_params.get('token')
    if not token:
        return Response({'error': _('Токен не надано.')}, status=status.HTTP_400_BAD_REQUEST)

    user_pk = verify_email_token(token)
    if user_pk is None:
        return Response({'error': _('Недійсне або прострочене посилання.')}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return Response({'error': _('Користувача не знайдено.')}, status=status.HTTP_400_BAD_REQUEST)

    if user.is_active:
        return Response({'message': _('Пошту вже підтверджено.')})

    user.is_active = True
    user.save(update_fields=['is_active'])
    return Response({'message': _('Пошту успішно підтверджено! Тепер ви можете увійти у свій аккаунт.')})


@extend_schema(
    tags=['Authentication'],
    summary='Request password reset',
    description='Sends a password reset email. Always returns 200 to prevent email enumeration.',
    request=inline_serializer('PasswordResetRequest', fields={'email': s.EmailField()}),
    responses={200: inline_serializer('PasswordResetResponse', fields={'message': s.CharField()})},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    email = request.data.get('email', '').strip()
    if email:
        try:
            user = User.objects.get(email=email, is_active=True)
            send_password_reset_email.delay(user.id)
        except User.DoesNotExist:
            pass
    return Response({'message': _('Якщо цю адресу зареєстровано, ми надіслали лист із інструкціями.')})


@extend_schema(
    tags=['Authentication'],
    summary='Confirm password reset',
    description='Sets a new password using uid and token from the reset email.',
    request=inline_serializer('PasswordResetConfirm', fields={
        'uid': s.CharField(),
        'token': s.CharField(),
        'password': s.CharField(),
        'password2': s.CharField(),
    }),
    responses={
        200: inline_serializer('PasswordResetConfirmSuccess', fields={'message': s.CharField()}),
        400: inline_serializer('PasswordResetConfirmError', fields={'error': s.CharField()}),
    },
)
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    uid = request.data.get('uid', '')
    token = request.data.get('token', '')
    password = request.data.get('password', '')
    password2 = request.data.get('password2', '')

    if not all([uid, token, password, password2]):
        return Response({'error': _('Усі поля є обов\'язковими.')}, status=status.HTTP_400_BAD_REQUEST)

    if password != password2:
        return Response({'error': _('Паролі не збігаються.')}, status=status.HTTP_400_BAD_REQUEST)

    if len(password) < 8:
        return Response({'error': _('Пароль має містити щонайменше 8 символів.')}, status=status.HTTP_400_BAD_REQUEST)

    user = verify_password_reset_token(uid, token)
    if user is None:
        return Response({'error': _('Недійсне або прострочене посилання.')}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)
    user.save(update_fields=['password'])
    return Response({'message': _('Пароль успішно змінено!')})


@extend_schema(
    tags=['Authentication'],
    summary='Resend verification email',
    description='Resends verification email for inactive accounts. Always returns 200.',
    request=inline_serializer('ResendVerification', fields={'email': s.EmailField()}),
    responses={200: inline_serializer('ResendVerificationResponse', fields={'message': s.CharField()})},
)
@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification(request):
    email = request.data.get('email', '').strip()
    if email:
        try:
            user = User.objects.get(email=email, is_active=False)
            send_verification_email.delay(user.id)
        except User.DoesNotExist:
            pass
    return Response({'message': _('Якщо цю адресу електронної пошти зареєстровано, ми надіслали лист для підтвердження.')})


@extend_schema_view(
    list=extend_schema(
        tags=['Tags'],
        summary='List all tags',
        description='Returns all available tags for cultural objects. No authentication required.',
        examples=[
            OpenApiExample(
                'Success response',
                value={'id': 1, 'name': 'UNESCO', 'slug': 'unesco', 'icon': '🟢'},
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=['Tags'],
        summary='Tag details',
        description='Returns a single tag by ID.',
        responses={200: TagSerializer, 404: ErrorResponse},
        examples=[
            OpenApiExample(
                'Success response',
                value={'id': 1, 'name': 'UNESCO', 'slug': 'unesco', 'icon': '🟢'},
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                'Not found',
                value={'detail': 'Not found.'},
                response_only=True,
                status_codes=['404'],
            ),
        ],
    ),
)
class TagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Tag.objects.all().order_by('name')
        tag_type = self.request.query_params.get('tag_type')
        if tag_type in ('object', 'event'):
            qs = qs.filter(tag_type=tag_type)
        return qs


@extend_schema_view(
    list=extend_schema(
        tags=['Objects'],
        summary='List objects',
        description='Guest sees only approved. Author sees approved + own. Admin sees all except archived.',
        parameters=[
            OpenApiParameter(name='tags', description='Filter by tag IDs (comma-separated, e.g. 1,3,5)', type=str),
            OpenApiParameter(name='search', description='Search by title and description', type=str),
        ],
        examples=[
            OpenApiExample(
                'Success response',
                value={
                    'id': 1,
                    'title': 'St. Andrew\'s Church',
                    'latitude': '50.459000',
                    'longitude': '30.517800',
                    'status': 'approved',
                    'author_name': 'alecs7turbo',
                    'tags': [{'id': 1, 'name': 'UNESCO', 'slug': 'unesco', 'icon': '🟢'}],
                    'created_at': '2026-03-20T12:00:00Z',
                },
                response_only=True,
            ),
        ],
    ),
    retrieve=extend_schema(
        tags=['Objects'],
        summary='Object details',
        description='Returns full object details including description, links, author, and dates. Visibility depends on user role.',
        responses={200: ObjectDetailSerializer, 404: ErrorResponse},
        examples=[
            OpenApiExample(
                'Success response',
                value={
                    'id': 1,
                    'title': 'St. Andrew\'s Church',
                    'description': 'Orthodox church in Kyiv, built in 1754.',
                    'latitude': '50.459000',
                    'longitude': '30.517800',
                    'status': 'approved',
                    'author': 'alecs7turbo',
                    'tags': [{'id': 1, 'name': 'UNESCO', 'slug': 'unesco', 'icon': '🟢'}],
                    'wikipedia_url': 'https://en.wikipedia.org/wiki/St_Andrew%27s_Church,_Kyiv',
                    'official_website': None,
                    'google_maps_url': None,
                    'created_at': '2026-03-20T12:00:00Z',
                    'updated_at': '2026-03-20T12:00:00Z',
                    'archived_at': None,
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                'Not found',
                value={'detail': 'Not found.'},
                response_only=True,
                status_codes=['404'],
            ),
        ],
    ),
    create=extend_schema(
        tags=['Objects'],
        summary='Create object',
        description='New object gets status "pending". Requires authentication.',
        responses={201: ObjectWriteSerializer, 400: ErrorResponse, 401: ErrorResponse},
        examples=[
            OpenApiExample(
                'Create request',
                value={
                    'title': 'St. Andrew\'s Church',
                    'description': 'Orthodox church in Kyiv, built in 1754.',
                    'latitude': 50.4590,
                    'longitude': 30.5178,
                    'tags': [1, 3],
                    'wikipedia_url': 'https://en.wikipedia.org/wiki/St_Andrew%27s_Church,_Kyiv',
                },
                request_only=True,
            ),
            OpenApiExample(
                'Success response',
                value={
                    'id': 42,
                    'title': 'St. Andrew\'s Church',
                    'description': 'Orthodox church in Kyiv, built in 1754.',
                    'latitude': '50.459000',
                    'longitude': '30.517800',
                    'tags': [1, 3],
                    'wikipedia_url': 'https://en.wikipedia.org/wiki/St_Andrew%27s_Church,_Kyiv',
                    'official_website': None,
                    'google_maps_url': None,
                },
                response_only=True,
                status_codes=['201'],
            ),
            OpenApiExample(
                'Validation error',
                value={'coordinates': ['Coordinates are outside Ukraine borders.'],
                       'tags': ['Object must have at least 1 tag.']},
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                'Unauthorized',
                value={'detail': 'Authentication credentials were not provided.'},
                response_only=True,
                status_codes=['401'],
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=['Objects'],
        summary='Update object (partial)',
        description='If author edits an approved object, status resets to pending. Admin edits keep the status.',
        responses={200: ObjectWriteSerializer, 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse,
                   404: ErrorResponse},
        examples=[
            OpenApiExample(
                'Update request',
                value={'title': 'Updated Title', 'description': 'Updated description.'},
                request_only=True,
            ),
            OpenApiExample(
                'Success response',
                value={
                    'id': 1,
                    'title': 'Updated Title',
                    'description': 'Updated description.',
                    'latitude': '50.459000',
                    'longitude': '30.517800',
                    'tags': [1],
                    'wikipedia_url': None,
                    'official_website': None,
                    'google_maps_url': None,
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                'Validation error',
                value={'coordinates': ['Coordinates are outside Ukraine borders.']},
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                'Unauthorized',
                value={'detail': 'Authentication credentials were not provided.'},
                response_only=True,
                status_codes=['401'],
            ),
            OpenApiExample(
                'Forbidden',
                value={'detail': 'You do not have permission to perform this action.'},
                response_only=True,
                status_codes=['403'],
            ),
            OpenApiExample(
                'Not found',
                value={'detail': 'Not found.'},
                response_only=True,
                status_codes=['404'],
            ),
        ],
    ),
    update=extend_schema(
        tags=['Objects'],
        summary='Update object (full)',
        description='Replaces all fields. Same re-moderation rules as partial update.',
        responses={200: ObjectWriteSerializer, 400: ErrorResponse, 401: ErrorResponse, 403: ErrorResponse,
                   404: ErrorResponse},
        examples=[
            OpenApiExample(
                'Update request',
                value={
                    'title': 'St. Andrew\'s Church',
                    'description': 'Updated description.',
                    'latitude': 50.4590,
                    'longitude': 30.5178,
                    'tags': [1, 2],
                },
                request_only=True,
            ),
            OpenApiExample(
                'Success response',
                value={
                    'id': 1,
                    'title': 'St. Andrew\'s Church',
                    'description': 'Updated description.',
                    'latitude': '50.459000',
                    'longitude': '30.517800',
                    'tags': [1, 2],
                    'wikipedia_url': None,
                    'official_website': None,
                    'google_maps_url': None,
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                'Validation error',
                value={'tags': ['Object must have at least 1 tag.']},
                response_only=True,
                status_codes=['400'],
            ),
            OpenApiExample(
                'Unauthorized',
                value={'detail': 'Authentication credentials were not provided.'},
                response_only=True,
                status_codes=['401'],
            ),
            OpenApiExample(
                'Forbidden',
                value={'detail': 'You do not have permission to perform this action.'},
                response_only=True,
                status_codes=['403'],
            ),
            OpenApiExample(
                'Not found',
                value={'detail': 'Not found.'},
                response_only=True,
                status_codes=['404'],
            ),
        ],
    ),
    destroy=extend_schema(
        tags=['Objects'],
        summary='Archive object',
        description='Soft delete — changes status to archived. Only admin can restore.',
        responses={
            200: inline_serializer('ArchiveResponse', fields={'detail': s.CharField()}),
            401: ErrorResponse,
            403: ErrorResponse,
            404: ErrorResponse,
        },
        examples=[
            OpenApiExample(
                'Success response',
                value={'detail': 'Object archived'},
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                'Unauthorized',
                value={'detail': 'Authentication credentials were not provided.'},
                response_only=True,
                status_codes=['401'],
            ),
            OpenApiExample(
                'Forbidden',
                value={'detail': 'You do not have permission to perform this action.'},
                response_only=True,
                status_codes=['403'],
            ),
            OpenApiExample(
                'Not found',
                value={'detail': 'Not found.'},
                response_only=True,
                status_codes=['404'],
            ),
        ],
    ),
)
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
                   .prefetch_related('tags')
                   .exclude(status='archived')
                   .annotate(favorites_count=Count('favorited_by', distinct=True))
                   .annotate(_cover_thumbnail_url=Subquery(cover_thumb_sq))
                   .order_by('-created_at'))

        if user.is_authenticated:
            base_qs = base_qs.annotate(
                _is_favorited=Exists(Favorite.objects.filter(user=user, cultural_object=OuterRef('pk')))
            )

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

        if not self.request.user.is_staff and is_approved and self._has_actual_changes(instance, serializer.validated_data):
            serializer.save(status='pending')
        else:
            serializer.save()

    @staticmethod
    def _has_actual_changes(instance, validated_data):
        """Перевіряє, чи дійсно змінились значення (PATCH тим самим контентом — no-op)."""
        for field, value in validated_data.items():
            if field == 'tags':
                current = set(instance.tags.values_list('id', flat=True))
                new = set(t.pk for t in value)
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
        tags=['Objects'],
        summary='My objects',
        description='List of current user\'s objects (excluding archived). Requires authentication.',
        responses={200: ObjectListSerializer(many=True), 401: ErrorResponse},
        examples=[
            OpenApiExample(
                'Success response',
                value={
                    'id': 1,
                    'title': 'St. Andrew\'s Church',
                    'latitude': '50.459000',
                    'longitude': '30.517800',
                    'status': 'pending',
                    'author_name': 'alecs7turbo',
                    'tags': [{'id': 1, 'name': 'UNESCO', 'slug': 'unesco', 'icon': '🟢'}],
                    'created_at': '2026-03-20T12:00:00Z',
                },
                response_only=True,
                status_codes=['200'],
            ),
            OpenApiExample(
                'Unauthorized',
                value={'detail': 'Authentication credentials were not provided.'},
                response_only=True,
                status_codes=['401'],
            ),
        ],
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my(self, request):
        objects = (CulturalObject.objects
                   .select_related('author')
                   .prefetch_related('tags')
                   .filter(author=request.user)
                   .exclude(status='archived')
                   .order_by('-created_at'))

        page = self.paginate_queryset(objects)
        if page is not None:
            serializer = ObjectListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ObjectListSerializer(objects, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Objects'],
        summary='Objects where I uploaded photos',
        description='Returns objects (own or others) where the current user has uploaded at least one photo. Each item includes a `my_photos` array with statuses.',
        responses={200: ObjectWithMyPhotosSerializer(many=True), 401: ErrorResponse},
    )
    @action(detail=False, methods=['get'], url_path='with-my-photos', permission_classes=[IsAuthenticated])
    def with_my_photos(self, request):
        object_ids = (ObjectPhoto.objects
                      .filter(uploaded_by=request.user)
                      .values_list('cultural_object_id', flat=True)
                      .distinct())

        objects = (CulturalObject.objects
                   .select_related('author')
                   .prefetch_related('tags', 'photos__uploaded_by')
                   .filter(id__in=object_ids)
                   .exclude(status='archived')
                   .order_by('-created_at'))

        page = self.paginate_queryset(objects)
        if page is not None:
            serializer = ObjectWithMyPhotosSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ObjectWithMyPhotosSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)

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

        page = self.paginate_queryset(objects)
        if page is not None:
            serializer = ObjectListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ObjectListSerializer(objects, many=True, context={'request': request})
        return Response(serializer.data)

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

        fav, created = FavoriteAuthor.objects.get_or_create(user=request.user, author=author)
        if not created:
            fav.delete()
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
        serializer = self.get_serializer(authors, many=True)
        return Response(serializer.data)


@extend_schema(
    tags=['System'],
    summary='Health check',
    description='Returns API status. Used for deployment verification and monitoring.',
    responses={200: inline_serializer('HealthResponse', fields={
        'status': s.CharField(),
        'message': s.CharField(),
    })},
    examples=[
        OpenApiExample(
            'Success response',
            value={'status': 'ok', 'message': 'API is running'},
            response_only=True,
        ),
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'ok', 'message': 'API is running'})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_preference(request):
    """Read or update current user's preference (language, theme)."""
    from .models import UserPreference
    pref, _created = UserPreference.objects.get_or_create(
        user=request.user,
        defaults={'language': 'uk'},
    )
    if request.method == 'PATCH':
        update_fields = []
        if 'language' in request.data:
            language = request.data.get('language')
            if language not in dict(UserPreference.Language.choices):
                return Response(
                    {'language': [_('Невірна мова. Доступні: uk, en.')]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pref.language = language
            update_fields.append('language')
        if 'theme' in request.data:
            theme = request.data.get('theme')
            if theme not in dict(UserPreference.Theme.choices):
                return Response(
                    {'theme': [_('Невірна тема. Доступні: light, dark.')]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pref.theme = theme
            update_fields.append('theme')
        if update_fields:
            update_fields.append('updated_at')
            pref.save(update_fields=update_fields)
    return Response({'language': pref.language, 'theme': pref.theme})


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
        qs = ObjectPhoto.objects.filter(cultural_object=cultural_object)

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
                status=status.HTTP_403_FORBIDDEN,
            )

        image = request.FILES.get('image')
        if not image:
            return Response({'detail': 'Поле image є обов\'язковим.'}, status=400)

        try:
            validate_image_size(image)
            validate_image_format(image)
        except ValidationError as e:
            return Response({'detail': e.message if hasattr(e, 'message') else str(e)}, status=400)

        user_count = ObjectPhoto.objects.filter(
            cultural_object=cultural_object,
            uploaded_by=request.user,
        ).exclude(status='rejected').count()
        max_user = (
            settings.PHOTO_MAX_PER_AUTHOR if is_author
            else settings.PHOTO_MAX_PER_CONTRIBUTOR
        )
        if user_count >= max_user:
            return Response(
                {'detail': f'Ліміт {max_user} фото на цей об\'єкт вичерпано.', 'code': 'user_limit_exceeded'},
                status=400,
            )

        total = ObjectPhoto.objects.filter(
            cultural_object=cultural_object,
        ).exclude(status='rejected').count()
        if total >= settings.PHOTO_MAX_PER_OBJECT:
            return Response(
                {'detail': f'Об\'єкт уже містить максимум {settings.PHOTO_MAX_PER_OBJECT} фото.', 'code': 'object_full'},
                status=400,
            )

        try:
            uploaded = cloudinary_service.upload_photo(image)
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception('Cloudinary upload failed: %s', e)
            return Response(
                {'detail': 'Не вдалося завантажити фото на сервер. Спробуйте пізніше.'},
                status=500,
            )

        # Atomic-блок з row-lock запобігає race condition при паралельних uploads:
        # сесія блокує parent-об'єкт, перевіряє ліміти ще раз, створює фото.
        from django.db import transaction
        try:
            with transaction.atomic():
                CulturalObject.objects.select_for_update().get(pk=cultural_object.pk)

                user_count_locked = ObjectPhoto.objects.filter(
                    cultural_object=cultural_object,
                    uploaded_by=request.user,
                ).exclude(status='rejected').count()
                if user_count_locked >= max_user:
                    raise _PhotoLimitExceeded('user_limit_exceeded', max_user)

                total_locked = ObjectPhoto.objects.filter(
                    cultural_object=cultural_object,
                ).exclude(status='rejected').count()
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
        except _PhotoLimitExceeded as e:
            # rollback: видалити Cloudinary-файл (бо ObjectPhoto не створено,
            # тож pre_delete-signal не спрацює)
            try:
                cloudinary_service.delete_photo(uploaded['public_id'])
            except Exception:
                pass
            if e.code == 'user_limit_exceeded':
                return Response(
                    {'detail': f'Ліміт {e.limit} фото на цей об\'єкт вичерпано.', 'code': 'user_limit_exceeded'},
                    status=400,
                )
            return Response(
                {'detail': f'Об\'єкт уже містить максимум {e.limit} фото.', 'code': 'object_full'},
                status=400,
            )

        return Response(ObjectPhotoSerializer(photo).data, status=201)

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


class InaccuracyReportViewSet(viewsets.GenericViewSet):
    """Crowd-sourced reports about issues with cultural objects.

    Endpoints:
      POST   /api/objects/<object_pk>/report/      — create report (auth, 1/day per object)
      DELETE /api/reports/<id>/                    — delete own pending report
      GET    /api/users/me/reports/                — list reports created by me
      GET    /api/users/me/objects/reports/        — list reports on objects I authored
      GET    /api/admin/reports/                   — admin queue (with status filter)
      POST   /api/admin/reports/<id>/resolve/      — admin: resolve
      POST   /api/admin/reports/<id>/dismiss/      — admin: dismiss
    """
    serializer_class = None  # set per-action

    def get_serializer_class(self):
        from .serializers import InaccuracyReportSerializer
        return InaccuracyReportSerializer

    def get_permissions(self):
        if self.action in ('admin_list', 'admin_resolve', 'admin_dismiss'):
            from rest_framework.permissions import IsAdminUser
            return [IsAdminUser()]
        return [IsAuthenticated()]


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_object(request, object_pk):
    from .models import InaccuracyReport
    from .serializers import InaccuracyReportSerializer
    from datetime import timedelta
    from django.utils import timezone

    try:
        obj = CulturalObject.objects.get(pk=object_pk)
    except CulturalObject.DoesNotExist:
        return Response({'detail': _('Об\'єкт не знайдено.')}, status=status.HTTP_404_NOT_FOUND)

    # Throttle: 1 report per (user, object) per 24h
    recent = InaccuracyReport.objects.filter(
        reporter=request.user,
        cultural_object=obj,
        created_at__gte=timezone.now() - timedelta(days=1),
    ).exists()
    if recent:
        return Response(
            {'detail': _('Ви вже надсилали репорт на цей об\'єкт нещодавно. Спробуйте через 24 години.')},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    reason_type = request.data.get('reason_type')
    if reason_type not in dict(InaccuracyReport.ReasonType.choices):
        return Response({'reason_type': [_('Невірна причина.')]}, status=status.HTTP_400_BAD_REQUEST)

    report = InaccuracyReport.objects.create(
        cultural_object=obj,
        reporter=request.user,
        reason_type=reason_type,
        note=request.data.get('note', '')[:500],
    )
    return Response(
        InaccuracyReportSerializer(report).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_own_report(request, report_pk):
    from .models import InaccuracyReport
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
    from .models import InaccuracyReport
    from .serializers import InaccuracyReportSerializer
    qs = InaccuracyReport.objects.filter(reporter=request.user).select_related('cultural_object')
    return Response(InaccuracyReportSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reports_on_my_objects(request):
    from .models import InaccuracyReport
    from .serializers import InaccuracyReportSerializer
    qs = (InaccuracyReport.objects
          .filter(cultural_object__author=request.user)
          .select_related('cultural_object', 'reporter'))
    return Response(InaccuracyReportSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_reports_list(request):
    from .models import InaccuracyReport
    from .serializers import InaccuracyReportSerializer
    if not request.user.is_staff:
        return Response({'detail': _('Тільки для адміністратора.')}, status=status.HTTP_403_FORBIDDEN)
    status_filter = request.query_params.get('status', 'pending')
    qs = InaccuracyReport.objects.select_related('cultural_object', 'reporter')
    if status_filter in dict(InaccuracyReport.Status.choices):
        qs = qs.filter(status=status_filter)
    return Response(InaccuracyReportSerializer(qs, many=True).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_resolve_report(request, report_pk):
    return _admin_close_report(request, report_pk, resolved=True)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_dismiss_report(request, report_pk):
    return _admin_close_report(request, report_pk, resolved=False)


def _admin_close_report(request, report_pk, resolved: bool):
    from .models import InaccuracyReport
    from .serializers import InaccuracyReportSerializer
    from django.utils import timezone
    if not request.user.is_staff:
        return Response({'detail': _('Тільки для адміністратора.')}, status=status.HTTP_403_FORBIDDEN)
    try:
        report = InaccuracyReport.objects.get(pk=report_pk)
    except InaccuracyReport.DoesNotExist:
        return Response({'detail': _('Репорт не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
    if report.status != InaccuracyReport.Status.PENDING:
        return Response(
            {'detail': _('Репорт уже опрацьовано.')},
            status=status.HTTP_400_BAD_REQUEST,
        )
    report.status = (
        InaccuracyReport.Status.RESOLVED if resolved else InaccuracyReport.Status.DISMISSED
    )
    report.admin_response = request.data.get('admin_response', '')[:500]
    report.resolved_by = request.user
    report.resolved_at = timezone.now()
    report.save(update_fields=['status', 'admin_response', 'resolved_by', 'resolved_at'])

    from .email import send_inaccuracy_outcome_email
    send_inaccuracy_outcome_email.delay(report.id)

    return Response(InaccuracyReportSerializer(report).data)


# --- Visit & PlannedVisit endpoints ---

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_visit(request, object_pk):
    """Toggle 'I visited' for the current user."""
    from .models import Visit, CulturalObject
    from .serializers import VisitSerializer
    try:
        obj = CulturalObject.objects.get(pk=object_pk)
    except CulturalObject.DoesNotExist:
        return Response({'detail': _('Об\'єкт не знайдено.')}, status=status.HTTP_404_NOT_FOUND)

    visit = Visit.objects.filter(user=request.user, cultural_object=obj).first()
    if visit:
        visit.delete()
        return Response({'is_visited': False})
    visit = Visit.objects.create(user=request.user, cultural_object=obj)
    return Response({'is_visited': True, 'visit': VisitSerializer(visit).data}, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_visit(request, visit_pk):
    """Edit own visit: impression, visited_at, is_public."""
    from .models import Visit
    from .serializers import VisitSerializer
    try:
        visit = Visit.objects.get(pk=visit_pk)
    except Visit.DoesNotExist:
        return Response({'detail': _('Візит не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
    if visit.user_id != request.user.id:
        return Response({'detail': _('Не можна редагувати чужий візит.')}, status=status.HTTP_403_FORBIDDEN)

    allowed = {'impression', 'visited_at', 'is_public'}
    updates = {k: v for k, v in request.data.items() if k in allowed}

    if 'visited_at' in updates:
        from datetime import date
        try:
            parsed = date.fromisoformat(str(updates['visited_at']))
        except ValueError:
            return Response({'visited_at': [_('Невірний формат дати.')]}, status=status.HTTP_400_BAD_REQUEST)
        if parsed > timezone.localdate():
            return Response(
                {'visited_at': [_('Дата візиту не може бути у майбутньому.')]},
                status=status.HTTP_400_BAD_REQUEST,
            )

    for k, v in updates.items():
        setattr(visit, k, v)
    visit.save()
    return Response(VisitSerializer(visit).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def visits_count(request, object_pk):
    """Public: how many unique users visited this object."""
    from .models import Visit
    count = Visit.objects.filter(cultural_object_id=object_pk).count()
    return Response({'visits_count': count})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_visits(request):
    from .models import Visit
    from .serializers import VisitSerializer
    qs = Visit.objects.filter(user=request.user).select_related('cultural_object')
    return Response(VisitSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_visits(request, username):
    from .models import Visit
    from .serializers import VisitSerializer
    try:
        target = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'detail': _('Користувача не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
    qs = Visit.objects.filter(user=target, is_public=True).select_related('cultural_object')
    return Response(VisitSerializer(qs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_visits_stats(request):
    """Aggregated counts for the cultural passport dashboard."""
    from .models import Visit, Tag
    from django.db.models import Count
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
    return Response({
        'total_visits': total,
        'total_approved_objects': total_objects,
        'by_tag': by_tag,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_planned_visit(request, object_pk):
    """Toggle 'I plan to visit' for the current user."""
    from .models import PlannedVisit
    from .serializers import PlannedVisitSerializer
    try:
        obj = CulturalObject.objects.get(pk=object_pk)
    except CulturalObject.DoesNotExist:
        return Response({'detail': _('Об\'єкт не знайдено.')}, status=status.HTTP_404_NOT_FOUND)

    planned = PlannedVisit.objects.filter(user=request.user, cultural_object=obj).first()
    if planned:
        planned.delete()
        return Response({'is_planned': False})
    planned = PlannedVisit.objects.create(user=request.user, cultural_object=obj)
    return Response(
        {'is_planned': True, 'planned': PlannedVisitSerializer(planned).data},
        status=status.HTTP_201_CREATED,
    )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_planned_visit(request, planned_pk):
    from .models import PlannedVisit
    from .serializers import PlannedVisitSerializer
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
    from .models import PlannedVisit, Visit
    from .serializers import VisitSerializer
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
    from .models import PlannedVisit
    from .serializers import PlannedVisitSerializer
    qs = PlannedVisit.objects.filter(user=request.user).select_related('cultural_object')
    return Response(PlannedVisitSerializer(qs, many=True).data)


# --- Routes ---

MAX_STOPS_PER_ROUTE = 50


class RouteViewSet(viewsets.ModelViewSet):
    """CRUD for Heritage Routes.

    Visibility:
      - public list: only approved routes
      - draft/pending visible to author + admin
    """
    lookup_field = 'slug'

    def get_serializer_class(self):
        from .serializers import RouteListSerializer, RouteDetailSerializer, RouteWriteSerializer
        if self.action == 'list':
            return RouteListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return RouteWriteSerializer
        return RouteDetailSerializer

    def get_queryset(self):
        from .models import Route
        qs = Route.objects.select_related('author').prefetch_related('tags', 'stops__cultural_object')
        user = self.request.user

        if self.action == 'list':
            qs = qs.filter(status=Route.Status.APPROVED)
            if self.request.query_params.get('is_featured') == 'true':
                qs = qs.filter(is_featured=True)
            tag_ids = self.request.query_params.get('tags')
            if tag_ids:
                ids = [int(t) for t in tag_ids.split(',') if t.isdigit()]
                if ids:
                    qs = qs.filter(tags__id__in=ids).distinct()
            return qs

        if self.action == 'retrieve':
            if user.is_authenticated:
                if user.is_staff:
                    return qs
                return qs.filter(Q(status=Route.Status.APPROVED) | Q(author=user))
            return qs.filter(status=Route.Status.APPROVED)

        return qs

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy',
                           'submit', 'copy', 'add_stop', 'reorder', 'remove_stop'):
            return [IsAuthenticated()]
        return [AllowAny()]

    def perform_create(self, serializer):
        from .models import Route
        serializer.save(author=self.request.user, status=Route.Status.DRAFT)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author_id != request.user.id and not request.user.is_staff:
            return Response({'detail': _('Не можна редагувати чужий маршрут.')},
                            status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        from .models import Route
        instance = self.get_object()
        if instance.author_id != request.user.id and not request.user.is_staff:
            return Response({'detail': _('Не можна видалити чужий маршрут.')},
                            status=status.HTTP_403_FORBIDDEN)
        instance.status = Route.Status.ARCHIVED
        instance.save(update_fields=['status', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def submit(self, request, slug=None):
        from .models import Route
        from .serializers import RouteDetailSerializer
        route = self.get_object()
        if route.author_id != request.user.id:
            return Response({'detail': _('Тільки автор може подати маршрут на модерацію.')},
                            status=status.HTTP_403_FORBIDDEN)
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
    def copy(self, request, slug=None):
        from .models import Route, RouteStop
        from .serializers import RouteDetailSerializer
        original = self.get_object()
        if original.status != Route.Status.APPROVED:
            return Response({'detail': _('Можна копіювати тільки опубліковані маршрути.')},
                            status=status.HTTP_403_FORBIDDEN)
        copy = Route.objects.create(
            title=f'{original.title} (копія)',
            description=original.description,
            author=request.user,
            status=Route.Status.DRAFT,
            cover_photo=original.cover_photo,
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
    def add_stop(self, request, slug=None):
        from .models import RouteStop
        from .serializers import RouteStopSerializer
        route = self.get_object()
        if route.author_id != request.user.id and not request.user.is_staff:
            return Response({'detail': _('Не можна редагувати чужий маршрут.')},
                            status=status.HTTP_403_FORBIDDEN)
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
        last_order = route.stops.count()
        stop = RouteStop.objects.create(
            route=route,
            cultural_object=cultural_object,
            order=last_order + 1,
            note=str(request.data.get('note', ''))[:500],
        )
        return Response(RouteStopSerializer(stop).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='reorder')
    def reorder(self, request, slug=None):
        from .models import RouteStop
        route = self.get_object()
        if route.author_id != request.user.id and not request.user.is_staff:
            return Response({'detail': _('Не можна редагувати чужий маршрут.')},
                            status=status.HTTP_403_FORBIDDEN)
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

    @action(detail=True, methods=['delete'], url_path=r'stops/(?P<stop_pk>\d+)')
    def remove_stop(self, request, slug=None, stop_pk=None):
        from .models import RouteStop
        route = self.get_object()
        if route.author_id != request.user.id and not request.user.is_staff:
            return Response({'detail': _('Не можна редагувати чужий маршрут.')},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            stop = RouteStop.objects.get(pk=stop_pk, route=route)
        except RouteStop.DoesNotExist:
            return Response({'detail': _('Зупинку не знайдено.')}, status=status.HTTP_404_NOT_FOUND)
        stop.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'], url_path='export')
    def export(self, request, slug=None):
        from .services.route_export import export_route_as_gpx, export_route_as_kml
        from django.http import HttpResponse
        route = self.get_object()
        fmt = request.query_params.get('format', 'gpx').lower()
        if fmt == 'gpx':
            content = export_route_as_gpx(route)
            content_type = 'application/gpx+xml'
            ext = 'gpx'
        elif fmt == 'kml':
            content = export_route_as_kml(route)
            content_type = 'application/vnd.google-earth.kml+xml'
            ext = 'kml'
        else:
            return Response({'detail': _('Підтримувані формати: gpx, kml.')},
                            status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{route.slug}.{ext}"'
        return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_routes(request):
    """List routes authored by the current user (any status)."""
    from .models import Route
    from .serializers import RouteListSerializer
    qs = (Route.objects.filter(author=request.user)
          .select_related('author').prefetch_related('tags')
          .order_by('-updated_at'))
    status_filter = request.query_params.get('status')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return Response(RouteListSerializer(qs, many=True, context={'request': request}).data)
