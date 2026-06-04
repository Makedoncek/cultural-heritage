"""OpenAPI schema declarations (drf-spectacular) for the view modules.

Only the large top-level blocks live here; short action-level @extend_schema
decorators stay next to their actions for readability.
"""
from drf_spectacular.utils import (
    OpenApiExample, OpenApiParameter, extend_schema, extend_schema_view, inline_serializer,
)
from rest_framework import serializers as s

from ..serializers import (
    ObjectDetailSerializer, ObjectListSerializer, ObjectWriteSerializer,
    RegisterSerializer, TagSerializer,
)

ErrorResponse = inline_serializer('ErrorResponse', fields={'detail': s.CharField()})


REGISTER_SCHEMA = extend_schema(
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

VERIFY_EMAIL_SCHEMA = extend_schema(
    tags=['Authentication'],
    summary='Verify email address',
    description='Activates user account via token from verification email.',
    parameters=[OpenApiParameter(name='token', type=str, location=OpenApiParameter.QUERY, required=True)],
    responses={
        200: inline_serializer('VerifyEmailSuccess', fields={'message': s.CharField()}),
        400: inline_serializer('VerifyEmailError', fields={'error': s.CharField()}),
    },
)

PASSWORD_RESET_SCHEMA = extend_schema(
    tags=['Authentication'],
    summary='Request password reset',
    description='Sends a password reset email. Always returns 200 to prevent email enumeration.',
    request=inline_serializer('PasswordResetRequest', fields={'email': s.EmailField()}),
    responses={200: inline_serializer('PasswordResetResponse', fields={'message': s.CharField()})},
)

PASSWORD_RESET_CONFIRM_SCHEMA = extend_schema(
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

RESEND_VERIFICATION_SCHEMA = extend_schema(
    tags=['Authentication'],
    summary='Resend verification email',
    description='Resends verification email for inactive accounts. Always returns 200.',
    request=inline_serializer('ResendVerification', fields={'email': s.EmailField()}),
    responses={200: inline_serializer('ResendVerificationResponse', fields={'message': s.CharField()})},
)

HEALTH_SCHEMA = extend_schema(
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

TAG_VIEWSET_SCHEMA = extend_schema_view(
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

OBJECT_VIEWSET_SCHEMA = extend_schema_view(
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
