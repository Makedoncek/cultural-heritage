from rest_framework import status, viewsets, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .filters import ObjectFilter
from .serializers import RegisterSerializer, TagSerializer
from .models import Tag
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import CulturalObject
from .serializers import ObjectListSerializer, ObjectDetailSerializer, ObjectWriteSerializer
from .permissions import IsAuthorOrReadOnly


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer
    permission_classes = [AllowAny]


class ObjectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = ObjectFilter
    search_fields = ['title', 'description']

    def get_serializer_class(self):
        if self.action == 'list':
            return ObjectListSerializer

        elif self.action in ['create', 'update', 'partial_update']:
            return ObjectWriteSerializer

        return ObjectDetailSerializer

    def get_queryset(self):
        user = self.request.user

        base_qs = CulturalObject.objects.exclude(status='archived')

        if user.is_staff:
            return base_qs

        if user.is_authenticated:
            return base_qs.filter(Q(status='approved') | Q(author=user)).distinct()

        return base_qs.filter(status='approved')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        is_approved = serializer.instance.status == 'approved'

        if not self.request.user.is_staff and is_approved:
            serializer.save(status='pending')
        else:
            serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.archive()
        return Response({'detail': "Об'єкт архівовано"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my(self, request):
        objects = (CulturalObject.objects.filter(author=request.user)
                   .exclude(status='archived').order_by('-created_at'))

        page = self.paginate_queryset(objects)
        if page is not None:
            serializer = ObjectListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ObjectListSerializer(objects, many=True)
        return Response(serializer.data)
