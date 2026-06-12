"""Shared helpers for view modules: lookups and ownership checks
that previously existed as ~15 copies of try/except + manual 403 returns."""
from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _
from rest_framework.exceptions import NotFound, PermissionDenied

DEFAULT_NOT_FOUND = 'Не знайдено.'
DEFAULT_OWNER_ONLY = 'Дозволено лише автору чи адміністратору.'


def toggle_membership(model, **lookup):
    """Race-safe toggle of a unique membership row (Favorite, Visit, …).

    Returns ``(created, instance)``: ``(True, obj)`` when the row was added,
    ``(False, None)`` when it was removed.

    Never raises IntegrityError under concurrent duplicate requests (double-tap,
    client retry). A plain get_or_create + delete still 500s when a parallel
    toggle deletes the row between get_or_create's failed INSERT and its recovery
    SELECT; here the only statement that can collide (the INSERT) is guarded and
    deletes never raise, so two concurrent toggles net to "removed" instead of an
    error. The unique constraint guarantees at most one row survives either way.
    """
    deleted = model.objects.filter(**lookup).delete()[0]
    if deleted:
        return False, None
    try:
        with transaction.atomic():
            return True, model.objects.create(**lookup)
    except IntegrityError:
        model.objects.filter(**lookup).delete()
        return False, None


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
