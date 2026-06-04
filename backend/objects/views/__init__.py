"""Views package — split by domain. Re-exports keep `from . import views`
usage in urls.py (and any external imports) working unchanged."""
from .auth import (
    password_reset_confirm, password_reset_request, register,
    resend_verification, verify_email,
)
from .system import health_check, user_preference
from .tags import TagViewSet
from .objects import ObjectViewSet
from .profiles import UserProfileViewSet
from .photos import ObjectPhotoViewSet
from .audio import ObjectAudioViewSet
from .routes import RouteViewSet, my_completed_routes, my_routes
from .reports import (
    create_report, delete_own_report, my_reports, report_object, reports_on_my_objects,
)
from .translations import (
    archive_my_translation, manage_my_translation, my_translations, restore_my_translation,
)
from .visits import (
    convert_planned_to_visit, my_planned_visits, my_visits, my_visits_stats,
    public_visits, public_visits_map, toggle_planned_visit, toggle_visit,
    update_planned_visit, update_visit, visits_count,
)

__all__ = [
    # auth
    'register', 'verify_email', 'password_reset_request', 'password_reset_confirm',
    'resend_verification',
    # system
    'health_check', 'user_preference',
    # viewsets
    'TagViewSet', 'ObjectViewSet', 'UserProfileViewSet',
    'ObjectPhotoViewSet', 'ObjectAudioViewSet', 'RouteViewSet',
    # routes
    'my_routes', 'my_completed_routes',
    # reports
    'create_report', 'report_object', 'delete_own_report', 'my_reports',
    'reports_on_my_objects',
    # translations
    'my_translations', 'manage_my_translation', 'archive_my_translation',
    'restore_my_translation',
    # visits
    'toggle_visit', 'update_visit', 'visits_count', 'my_visits', 'my_visits_stats',
    'public_visits', 'public_visits_map', 'toggle_planned_visit',
    'update_planned_visit', 'convert_planned_to_visit', 'my_planned_visits',
]
