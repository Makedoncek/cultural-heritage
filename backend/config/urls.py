"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from drf_spectacular.utils import extend_schema, OpenApiExample
from objects.serializers import CustomTokenObtainPairSerializer


@extend_schema(
    tags=['Authentication'],
    summary='Login (obtain JWT tokens)',
    description='Authenticates user and returns access + refresh JWT tokens. Access token contains username and is_staff claims.',
    examples=[
        OpenApiExample(
            'Request',
            value={'username': 'alecs7turbo', 'password': 'SecurePass123!'},
            request_only=True,
        ),
        OpenApiExample(
            'Success response',
            value={'access': 'eyJhbGciOiJIUzI1NiIs...', 'refresh': 'eyJhbGciOiJIUzI1NiIs...'},
            response_only=True,
            status_codes=['200'],
        ),
        OpenApiExample(
            'Invalid credentials',
            value={'detail': 'No active account found with the given credentials'},
            response_only=True,
            status_codes=['401'],
        ),
    ],
)
class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    tags=['Authentication'],
    summary='Refresh access token',
    description='Returns a new access token using a valid refresh token. Refresh tokens are rotated on use.',
    examples=[
        OpenApiExample(
            'Request',
            value={'refresh': 'eyJhbGciOiJIUzI1NiIs...'},
            request_only=True,
        ),
        OpenApiExample(
            'Success response',
            value={'access': 'eyJhbGciOiJIUzI1NiIs...'},
            response_only=True,
            status_codes=['200'],
        ),
        OpenApiExample(
            'Invalid or expired token',
            value={'detail': 'Token is invalid or expired', 'code': 'token_not_valid'},
            response_only=True,
            status_codes=['401'],
        ),
    ],
)
class CustomRefreshView(TokenRefreshView):
    pass


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/login/', CustomLoginView.as_view(), name='token_obtain'),
    path('api/auth/refresh/', CustomRefreshView.as_view(), name='token_refresh'),
    path('api/', include('objects.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    ]
