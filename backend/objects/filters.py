from django.utils import timezone
from django_filters import rest_framework as filters
from .models import CulturalObject


class EventStatusFilter(filters.CharFilter):
    """Filter events by status: active (happening now) or upcoming (starts in the future)."""

    def filter(self, qs, value):
        if not value:
            return qs
        now = timezone.now()
        if value == 'active':
            return qs.filter(event_start_date__lte=now, event_end_date__gte=now)
        if value == 'upcoming':
            return qs.filter(event_start_date__gt=now)
        return qs


class ObjectFilter(filters.FilterSet):
    tags = filters.BaseInFilter(field_name='tags__id', lookup_expr='in')
    object_type = filters.ChoiceFilter(choices=CulturalObject.ObjectType.choices)
    event_status = EventStatusFilter()
    author = filters.CharFilter(field_name='author__username')

    class Meta:
        model = CulturalObject
        fields = ['tags', 'object_type', 'event_status', 'author']
