"""System endpoints: health check, scheduled maintenance and per-user interface preferences."""
import hmac

from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework import status
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import UserPreference
from ..tasks import run_maintenance
from .schemas import HEALTH_SCHEMA


@HEALTH_SCHEMA
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'ok', 'message': 'API is running'})


@extend_schema(exclude=True)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def maintenance(request):
    """Run the celery-beat periodic tasks synchronously (for hosts without a beat process).

    Guarded by the X-Maintenance-Token header; disabled (404) when MAINTENANCE_TOKEN is unset.
    """
    expected = settings.MAINTENANCE_TOKEN
    if not expected:
        return Response(status=status.HTTP_404_NOT_FOUND)
    provided = request.headers.get('X-Maintenance-Token', '')
    if not hmac.compare_digest(provided.encode(), expected.encode()):
        return Response(status=status.HTTP_403_FORBIDDEN)
    return Response(run_maintenance())


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def user_preference(request):
    """Read or update current user's preference (language, theme)."""
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
