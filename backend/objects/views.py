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
from django.db.models import Q
from .models import CulturalObject
from .serializers import ObjectListSerializer, ObjectDetailSerializer, ObjectWriteSerializer
from .permissions import IsAuthorOrReadOnly

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
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    permission_classes = [AllowAny]


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
                   .exclude(status='archived'))

        if user.is_staff:
            return base_qs

        if user.is_authenticated:
            return base_qs.filter(Q(status='approved') | Q(author=user)).distinct()

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
