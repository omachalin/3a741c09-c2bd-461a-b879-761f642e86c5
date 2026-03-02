import django_filters as filters
from .models import (Page, MenuItem)


class MenuItemFilter(filters.FilterSet):
    code = filters.CharFilter(field_name='type_menu_fk__code', lookup_expr='exact')

    class Meta:
        model = MenuItem
        fields = ['code']


class PageFilter(filters.FilterSet):
    slug = filters.CharFilter(lookup_expr='exact')

    class Meta:
        model = Page
        fields = ['slug']
