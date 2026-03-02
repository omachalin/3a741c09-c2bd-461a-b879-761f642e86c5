from django.urls import path
from .serializers import MyTokenObtainPairSerializer
from .views import (UserViewSet, GetSeedsViewSet, Currency)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.views import TokenObtainPairView

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

router = DefaultRouter()
router.register(r'', UserViewSet, basename='user')
router.register(r'seeds', GetSeedsViewSet, basename='seeds')
router.register(r'currency', Currency, basename='currency')

urlpatterns = [
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

urlpatterns += router.urls
