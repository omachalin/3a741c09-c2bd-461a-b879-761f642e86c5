from .models import (Blog)
from .serializers import BlogSerializer, BlogPreviewSerializer
from .pagination import Pagination
# from .filters import PageFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from django.shortcuts import get_object_or_404


class BlogViewSet(viewsets.ModelViewSet):
    queryset = (
        Blog.objects.filter(is_active=True)
        .select_related('author_fk', 'image_fk')
        .order_by('-created_at')
    )
    serializer_class = BlogSerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = Pagination
    http_method_names = ['get']
    lookup_field = 'slug'

    view_permissions = {
        'list': {'admin': True, 'user': True, 'anon': True},
        'retrieve': {'admin': True, 'user': True, 'anon': True},
    }

    def get_serializer_class(self):
        if self.basename == 'img-preview':
            return BlogPreviewSerializer
        return BlogSerializer
