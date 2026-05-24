"""Registry mapping report target types to their model, owner, display title and URL.

Adding a new reportable content type = one entry here (plus a frontend reason set).
"""
from .models import (
    CulturalObject, Route, ObjectPhoto, ObjectAudio,
    CulturalObjectTranslation, RouteTranslation,
)


def _photo_title(p):
    return p.caption or f'Фото #{p.id}'


TARGET_TYPES = {
    'object': {
        'model': CulturalObject,
        'owner_id': lambda o: o.author_id,
        'title': lambda o: o.title,
        'url': lambda o: f'/objects/{o.id}',
    },
    'route': {
        'model': Route,
        'owner_id': lambda o: o.author_id,
        'title': lambda o: o.title,
        'url': lambda o: f'/routes/{o.id}',
    },
    'photo': {
        'model': ObjectPhoto,
        'owner_id': lambda o: o.uploaded_by_id,
        'title': _photo_title,
        'url': lambda o: f'/objects/{o.cultural_object_id}',
    },
    'audio': {
        'model': ObjectAudio,
        'owner_id': lambda o: o.uploaded_by_id,
        'title': lambda o: o.title,
        'url': lambda o: f'/objects/{o.cultural_object_id}',
    },
    'object_translation': {
        'model': CulturalObjectTranslation,
        'owner_id': lambda o: o.submitted_by_id,
        'title': lambda o: f'[{o.language}] {o.title}',
        'url': lambda o: f'/objects/{o.cultural_object_id}',
    },
    'route_translation': {
        'model': RouteTranslation,
        'owner_id': lambda o: o.submitted_by_id,
        'title': lambda o: f'[{o.language}] {o.title}',
        'url': lambda o: f'/routes/{o.route_id}',
    },
}


def resolve_target(target_type, target_id):
    """Return (instance, config) for a target, or (None, None) if unknown type / not found."""
    cfg = TARGET_TYPES.get(target_type)
    if not cfg:
        return None, None
    try:
        instance = cfg['model'].objects.get(pk=target_id)
    except (cfg['model'].DoesNotExist, ValueError, TypeError):
        return None, None
    return instance, cfg


def target_type_for_instance(instance):
    for ttype, cfg in TARGET_TYPES.items():
        if isinstance(instance, cfg['model']):
            return ttype
    return None


def describe_target(instance):
    """Return {target_type, target_title, target_url} for a resolved GFK target instance."""
    if instance is None:
        return {'target_type': None, 'target_title': '(видалено)', 'target_url': None}
    ttype = target_type_for_instance(instance)
    cfg = TARGET_TYPES.get(ttype)
    if not cfg:
        return {'target_type': ttype, 'target_title': str(instance), 'target_url': None}
    return {
        'target_type': ttype,
        'target_title': cfg['title'](instance),
        'target_url': cfg['url'](instance),
    }
