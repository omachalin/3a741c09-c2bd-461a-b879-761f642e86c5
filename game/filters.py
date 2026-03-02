import django_filters as filters
from .models import Game


class GameFilter(filters.FilterSet):
    name = filters.CharFilter(method='filter_name')

    class Meta:
        model = Game
        fields = (
            'name',
            'slug',
            'code',
        )

    def filter_name(self, queryset, name, value):
        if len(value) < 3:
            return queryset.none()
        return queryset.filter(name__icontains=value)
