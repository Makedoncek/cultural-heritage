"""Tag catalog (read-only)."""
from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from ..models import Tag
from ..serializers import TagSerializer
from .schemas import TAG_VIEWSET_SCHEMA


@TAG_VIEWSET_SCHEMA
class TagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Tag.objects.all().order_by('name')
        tag_type = self.request.query_params.get('tag_type')
        if tag_type in ('object', 'event'):
            qs = qs.filter(tag_type=tag_type)
        return qs
