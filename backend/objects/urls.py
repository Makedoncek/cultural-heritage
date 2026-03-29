from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('tags', views.TagViewSet, basename='tag')
router.register('objects', views.ObjectViewSet, basename='object')

app_name = 'objects'

urlpatterns = [
    path('auth/register/', views.register, name='register'),
    path('auth/verify-email/', views.verify_email, name='verify_email'),
    path('auth/password-reset/', views.password_reset_request, name='password_reset'),
    path('auth/password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    path('auth/resend-verification/', views.resend_verification, name='resend_verification'),
    path('health/', views.health_check, name='health_check'),
] + router.urls
