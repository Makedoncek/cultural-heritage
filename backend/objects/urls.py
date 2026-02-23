from django.urls import path
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('tags', views.TagViewSet, basename='tag')

app_name = 'objects'

urlpatterns = [
    path('auth/register/', views.register, name='register'),
] + router.urls
