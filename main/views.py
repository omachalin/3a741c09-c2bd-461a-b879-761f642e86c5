from .models import (Page, MenuItem)
from .serializers import MenuItemSerializer, PageSerializer
from .pagination import Pagination
from .filters import PageFilter, MenuItemFilter
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from casino.minio import MinioService
from django.shortcuts import render
from rest_framework.renderers import JSONRenderer


class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.all().order_by('created_at')
    serializer_class = PageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = PageFilter
    pagination_class = Pagination
    http_method_names = ['get']

    view_permissions = {
        'list': {'admin': True},
        'by_slug': {'admin': True, 'user': True, 'anon': True}
    }

    @action(detail=False, methods=['get'], url_path='by-slug')
    def by_slug(self, request):
        slug = request.query_params.get('slug')
        if not slug:
            return Response({'detail': 'slug required'}, status=400)

        page = get_object_or_404(Page, slug=slug)
        return Response(self.get_serializer(page).data)


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all().select_related('page_fk', 'type_menu_fk').order_by('order')
    serializer_class = MenuItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MenuItemFilter
    pagination_class = Pagination
    http_method_names = ['get']
    renderer_classes = [JSONRenderer]

    view_permissions = {
        'list': {'admin': True, 'user': True, 'anon': True}
    }


class MinioPublicView(APIView):
    view_permissions = {
        'get': {'admin': True, 'user': True, 'anon': True},
    }

    def get(self, request, filename, public=True):
        minio = MinioService(use_public=public)
        try:
            url = minio.generate_presigned_url(filename)
            return Response({'url': url})
        except minio.client.exceptions.NoSuchKey:
            return Response({'detail': 'File not found'}, status=404)


class MainView(APIView):
    view_permissions = {
        'get': {'admin': True, 'user': True, 'anon': True},
    }

    def get(self, request, *args, **kwargs):
        return render(request, "index.html")
