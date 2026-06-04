"""System endpoints: health check and per-user interface preferences."""
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import UserPreference
from .schemas import HEALTH_SCHEMA


@HEALTH_SCHEMA
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'ok', 'message': 'API is running'})


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
