from django.urls import path
from .views import (BlogViewSet)
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'all', BlogViewSet, basename='blog')
router.register(r'img-preview', BlogViewSet, basename='img-preview')

urlpatterns = [

]

urlpatterns += router.urls
