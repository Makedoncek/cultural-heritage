from django.apps import AppConfig


# Stable order of admin sections (by app_label) — independent of UI language.
# Without this, Django admin sorts apps alphabetically by their *translated*
# display name, so switching uk↔en reshuffles the index page.
ADMIN_APP_ORDER = {
    'objects': 0,
    'auth': 1,
    'token_blacklist': 2,
}


def _stable_get_app_list(original):
    def wrapper(self, request, app_label=None):
        app_list = original(self, request, app_label)
        return sorted(
            app_list,
            key=lambda app: ADMIN_APP_ORDER.get(app['app_label'], 99),
        )
    return wrapper


class ObjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'objects'
    verbose_name = 'CultureMap'

    def ready(self):
        from . import signals  # noqa: F401
        from django.contrib import admin
        admin.AdminSite.get_app_list = _stable_get_app_list(admin.AdminSite.get_app_list)
