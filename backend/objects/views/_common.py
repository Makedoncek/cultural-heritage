"""Shared helpers for view modules: lookups and ownership checks
that previously existed as ~15 copies of try/except + manual 403 returns."""
from django.utils.translation import gettext as _
from rest_framework.exceptions import NotFound, PermissionDenied

DEFAULT_NOT_FOUND = 'Не знайдено.'
DEFAULT_OWNER_ONLY = 'Дозволено лише автору чи адміністратору.'


def get_or_404(model, message=None, **filters):
    """Fetch a model instance or raise DRF NotFound with a Ukrainian detail message."""
    try:
        return model.objects.get(**filters)
    except model.DoesNotExist:
        raise NotFound(_(message or DEFAULT_NOT_FOUND))


def require_owner_or_staff(request, owner_id, message=None):
    """Raise PermissionDenied unless the request user owns the object or is staff."""
    if owner_id != request.user.id and not request.user.is_staff:
        raise PermissionDenied(_(message or DEFAULT_OWNER_ONLY))
