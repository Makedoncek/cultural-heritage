from rest_framework import status, viewsets, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, inline_serializer
from rest_framework import serializers as s
from .filters import ObjectFilter
from .serializers import RegisterSerializer, TagSerializer, CustomTokenObtainPairSerializer
from .email import send_verification_email, send_password_reset_email, verify_email_token, verify_password_reset_token
from .models import Tag
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Exists, OuterRef
from .models import CulturalObject, Favorite, FavoriteAuthor
from .serializers import ObjectListSerializer, ObjectDetailSerializer, ObjectWriteSerializer, UserProfileSerializer
from .permissions import IsAuthorOrReadOnly, IsPhotoUploaderOrAdmin, IsObjectAuthor
from .throttles import PhotoUploadThrottle
from .validators import validate_image_size, validate_image_format
from . import cloudinary_service
from .models import ObjectPhoto
from .serializers import ObjectPhotoSerializer
from rest_framework.parsers import MultiPartParser, FormParser
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
            'message': 'Реєстрація успішна! Перевірте вашу електронну пошту для підтвердження.',
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
        return Response({'error': 'Токен не надано.'}, status=status.HTTP_400_BAD_REQUEST)

    user_pk = verify_email_token(token)
    if user_pk is None:
        return Response({'error': 'Недійсне або прострочене посилання.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return Response({'error': 'Користувача не знайдено.'}, status=status.HTTP_400_BAD_REQUEST)

    if user.is_active:
        return Response({'message': 'Пошту вже підтверджено.'})

    user.is_active = True
    user.save(update_fields=['is_active'])
    return Response({'message': 'Пошту успішно підтверджено! Тепер ви можете увійти у свій аккаунт.'})


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
    return Response({'message': 'Якщо цю адресу зареєстровано, ми надіслали лист із інструкціями.'})


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
        return Response({'error': 'Усі поля є обов\'язковими.'}, status=status.HTTP_400_BAD_REQUEST)

    if password != password2:
        return Response({'error': 'Паролі не збігаються.'}, status=status.HTTP_400_BAD_REQUEST)

    if len(password) < 8:
        return Response({'error': 'Пароль має містити щонайменше 8 символів.'}, status=status.HTTP_400_BAD_REQUEST)

    user = verify_password_reset_token(uid, token)
    if user is None:
        return Response({'error': 'Недійсне або прострочене посилання.'}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)
    user.save(update_fields=['password'])
    return Response({'message': 'Пароль успішно змінено!'})


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
    return Response({'message': 'Якщо цю адресу електронної пошти зареєстровано, ми надіслали лист для підтвердження.'})


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

        base_qs = (CulturalObject.objects
                   .select_related('author')
                   .prefetch_related('tags')
                   .exclude(status='archived')
                   .annotate(favorites_count=Count('favorited_by', distinct=True))
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
        is_approved = serializer.instance.status == 'approved'

        if not self.request.user.is_staff and is_approved:
            serializer.save(status='pending')
        else:
            serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.archive()
        return Response({'detail': "Об'єкт архівовано"}, status=status.HTTP_200_OK)

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
            return Response({'detail': 'Користувача не знайдено.'}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({'detail': 'Користувача не знайдено.'}, status=status.HTTP_404_NOT_FOUND)

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
            return Response({'detail': 'Користувача не знайдено.'}, status=status.HTTP_404_NOT_FOUND)

        if request.user == author:
            return Response({'detail': 'Не можна підписатися на себе.'}, status=status.HTTP_400_BAD_REQUEST)

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


class ObjectPhotoViewSet(viewsets.GenericViewSet):
    """Управління фото культурного об'єкта (nested під /api/objects/<object_pk>/photos/)."""
    serializer_class = ObjectPhotoSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action == 'reorder':
            return [IsObjectAuthor()]
        if self.action in ('destroy', 'partial_update'):
            return [IsAuthenticated(), IsPhotoUploaderOrAdmin()]
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
            return Response({'detail': f'Помилка завантаження: {e}'}, status=500)

        order = 0
        if is_author:
            existing_orders = list(
                ObjectPhoto.objects.filter(
                    cultural_object=cultural_object,
                    is_author_photo=True,
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
        return Response(ObjectPhotoSerializer(photo).data, status=201)
