from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from . import views

router = DefaultRouter()
router.register('tags', views.TagViewSet, basename='tag')
router.register('objects', views.ObjectViewSet, basename='object')
router.register('users', views.UserProfileViewSet, basename='user-profile')

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
] + router.urls + photos_router.urls
