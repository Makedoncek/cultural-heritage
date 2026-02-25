from django_filters import rest_framework as filters
from .models import CulturalObject


class ObjectFilter(filters.FilterSet):
    tags = filters.BaseInFilter(field_name='tags__id', lookup_expr='in')

    class Meta:
        model = CulturalObject
        fields = ['tags']
