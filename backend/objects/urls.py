from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from . import views

router = DefaultRouter()
router.register('tags', views.TagViewSet, basename='tag')
router.register('objects', views.ObjectViewSet, basename='object')
router.register('users', views.UserProfileViewSet, basename='user-profile')
router.register('routes', views.RouteViewSet, basename='route')

photos_router = NestedDefaultRouter(router, 'objects', lookup='object')
photos_router.register('photos', views.ObjectPhotoViewSet, basename='object-photos')

app_name = 'objects'

urlpatterns = [
    path('auth/register/', views.register, name='register'),
    path('auth/verify-email/', views.verify_email, name='verify_email'),
    path('auth/password-reset/', views.password_reset_request, name='password_reset'),
    path('auth/password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    path('auth/resend-verification/', views.resend_verification, name='resend_verification'),
    path('health/', views.health_check, name='health_check'),
    path('me/preference/', views.user_preference, name='user_preference'),

    # Inaccuracy reports
    path('objects/<int:object_pk>/report/', views.report_object, name='report_object'),
    path('reports/<int:report_pk>/', views.delete_own_report, name='delete_own_report'),
    path('users/me/reports/', views.my_reports, name='my_reports'),
    path('users/me/objects/reports/', views.reports_on_my_objects, name='reports_on_my_objects'),
    path('admin/reports/', views.admin_reports_list, name='admin_reports_list'),
    path('admin/reports/<int:report_pk>/resolve/', views.admin_resolve_report, name='admin_resolve_report'),
    path('admin/reports/<int:report_pk>/dismiss/', views.admin_dismiss_report, name='admin_dismiss_report'),

    # Visits
    path('objects/<int:object_pk>/visit/', views.toggle_visit, name='toggle_visit'),
    path('objects/<int:object_pk>/visits-count/', views.visits_count, name='visits_count'),
    path('visits/<int:visit_pk>/', views.update_visit, name='update_visit'),
    path('users/me/visits/', views.my_visits, name='my_visits'),
    path('users/me/visits/stats/', views.my_visits_stats, name='my_visits_stats'),
    path('users/<str:username>/visits/', views.public_visits, name='public_visits'),

    # Planned visits
    path('objects/<int:object_pk>/plan-visit/', views.toggle_planned_visit, name='toggle_planned_visit'),
    path('planned-visits/<int:planned_pk>/', views.update_planned_visit, name='update_planned_visit'),
    path('planned-visits/<int:planned_pk>/convert-to-visit/', views.convert_planned_to_visit, name='convert_planned_to_visit'),
    path('users/me/planned-visits/', views.my_planned_visits, name='my_planned_visits'),

    # Routes
    path('users/me/routes/', views.my_routes, name='my_routes'),
] + router.urls + photos_router.urls
