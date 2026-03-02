import django_filters as filters
from .models import (User)


class UserFilter(filters.FilterSet):
    username = filters.CharFilter(lookup_expr='exact')
    class Meta:
        model = User
        fields = ['id', 'username']
