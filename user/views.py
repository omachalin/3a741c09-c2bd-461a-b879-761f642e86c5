from rest_framework import viewsets
from .models import User
from .serializers import SelfUserSerializer, OtherUserSerializer
from .pagination import Pagination
from .filters import UserFilter
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.response import Response
from .func import get_user_balances, generate_seeds, get_user_current_currency
from rest_framework_roles.granting import is_self
from rest_framework.viewsets import ViewSet
from user.redis.services.currency import CurrencyService


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('date_joined').select_related(
        'avatar_fk'
    ).prefetch_related(
        'balances__currency_fk',
        'fair_chains'
    )
    serializer_class = SelfUserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter
    pagination_class = Pagination
    http_method_names = ['get', 'post', 'patch', 'delete']

    view_permissions = {
        'me': {'admin': True, 'user': True},
        'balance': {'admin': True, 'user': True},
        'retrieve': {'admin': True, 'user': True},
        'partial_update': {
            'admin': True,
            'user': is_self,
        },
    }

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return SelfUserSerializer

        if self.action == 'retrieve':
            user = self.get_object()
            return SelfUserSerializer if (
                self.request.user.is_staff or
                self.request.user.is_superuser or
                user.id == self.request.user.id
            ) else OtherUserSerializer
        return SelfUserSerializer

    @action(detail=False, methods=['get'])
    def balance(self, request):
        balances = get_user_balances(request.user.id)
        return Response(balances)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = SelfUserSerializer(request.user)
        return Response(serializer.data)


class GetSeedsViewSet(ViewSet):
    queryset = None
    serializer_class = None

    view_permissions = {
        'get_seeds': {'admin': True, 'user': True, 'anon': True},
    }

    @action(detail=False, methods=['post'], url_path='get')
    def get_seeds(self, request):
        return Response(generate_seeds())


class Currency(ViewSet):
    queryset = None
    serializer_class = None

    http_method_names = ['post']

    view_permissions = {
        'change_currency': {'admin': True, 'user': True},
    }

    @action(detail=False, methods=['post'], url_path='change-currency')
    def change_currency(self, request):
        code = request.data.get('code')

        if not code:
            return Response({'error': 'code required'}, status=400)

        response = CurrencyService(user_id=request.user.id).change_currency(new_currency_code=code)

        return Response(response)
