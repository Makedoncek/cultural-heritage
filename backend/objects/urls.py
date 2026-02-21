from django.urls import path
from . import views

app_name = 'objects'

urlpatterns = [
    path('auth/register/', views.register, name='register'),
]
