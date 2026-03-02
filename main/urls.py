from rest_framework import routers
from django.urls import path
from .views import (MenuItemViewSet, PageViewSet, MinioPublicView, MainView)

urlpatterns = [
    path('file/<str:filename>/', MinioPublicView.as_view(), name='minio-image'),
    path(r".*", MainView.as_view(), name='main-view'),
]

router = routers.DefaultRouter()
router.register(r'menu-item', MenuItemViewSet, basename='menu_item')
router.register(r'page', PageViewSet, basename='page')

urlpatterns += router.urls
