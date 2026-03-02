from rest_framework import viewsets
from .models import Game, GameCategory, GameHistory
from .serializers import (
    GameSerializer, GameCategorySerializer, CoinFlipSerializer, GameHistorySerializer, BlackJackSerializer,
    GameHistoryStatsSerializer, GameHistoryTop10Serializer, ThreeSevensSerializer, SlotSerializer
)
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from .pagination import Pagination
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from game.services.coinflip import CoinFlipGame
from game.services.blackjack import BlackJackGame
from game.services.three_sevens import ThreeSevensGame
from game.services.slots import SlotsGame
from rest_framework import status
from game.services.base_func import get_game_config
from .filters import GameFilter


class GameCategoryViewSet(viewsets.ModelViewSet):
    queryset = (
        GameCategory.objects
        .prefetch_related(
            models.Prefetch(
                'game_set',
                queryset=Game.objects
                    .select_related('image_fk')
                    .order_by('order')
            )
        )
        .order_by('order')
    )
    serializer_class = GameCategorySerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = Pagination
    http_method_names = ['get']

    view_permissions = {
        'list': {'admin': True, 'user': True, 'anon': True},
        'retrieve': {'admin': True, 'user': True},
    }


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all().select_related(
        'category_fk', 'image_fk'
    ).prefetch_related('config').order_by('order')
    serializer_class = GameSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = GameFilter
    pagination_class = Pagination
    http_method_names = ['get']

    view_permissions = {
        'list': {'admin': True, 'user': True, 'anon': True},
        'retrieve': {'admin': True, 'user': True},
    }


class GameHistoryViewSet(viewsets.ModelViewSet):
    queryset = (
        GameHistory.objects
        .select_related('user_fk', 'game_fk', 'pf_chain_fk')
        .order_by('-created_at')
    )
    serializer_class = GameHistorySerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = Pagination
    http_method_names = ['get']

    view_permissions = {
        'list': {'admin': True},
    }


class StatsViewSet(GameHistoryViewSet):
    view_permissions = {
        'top_wins': {'admin': True, 'user': True, 'anon': True},
        'last_10_games': {'admin': True, 'user': True, 'anon': True},
    }

    @action(detail=False, methods=['get'], url_path='last-10-games')
    def last_10_games(self, request):
        qs = self.get_queryset()

        if 'code' in request.query_params:
            qs = qs.filter(game_fk__code=request.query_params['code'])

        last_10 = qs[:10]
        big_wins = qs.filter(payout__gt=5000)[:10]

        return Response({
            'last_10': GameHistoryTop10Serializer(last_10, many=True).data,
            'big_wins': GameHistoryTop10Serializer(big_wins, many=True).data,
        })

    @action(detail=False, methods=['get'], url_path='top-wins')
    def top_wins(self, request):

        code = request.query_params.get('code')
        if not code:
            return Response({'error': 'code required'}, status=400)

        top_payout = GameHistory.objects.select_related('user_fk', 'game_fk').filter(
            game_fk__code=code,
            payout__gt=0
        ).order_by('-payout')[:3]

        top_multiplier = GameHistory.objects.select_related('user_fk', 'game_fk').filter(
            game_fk__code=code,
            multiplier__gt=0
        ).order_by('-multiplier')[:3]

        serializer_payout = GameHistoryStatsSerializer(top_payout, many=True)
        serializer_multiplier = GameHistoryStatsSerializer(top_multiplier, many=True)

        return Response({
            'top_payout': serializer_payout.data,
            'top_multiplier': serializer_multiplier.data,
        })


class GameConfig(ViewSet):
    queryset = None
    serializer_class = None

    http_method_names = ['get']

    view_permissions = {
        'config': {'admin': True, 'user': True, 'anon': True},
    }

    @action(detail=False, methods=['get'], url_path='get')
    def config(self, request):
        code = request.query_params.get('code')

        if not code:
            return Response({'error': 'code required'}, status=400)

        return Response(get_game_config(code=code))


class CoinFlipViewSet(ViewSet):
    queryset = None
    serializer_class = None

    view_permissions = {
        'play': {'admin': True, 'user': True},
        'collect': {'admin': True, 'user': True},
    }

    @action(detail=False, methods=['post'], url_path='collect')
    def collect(self, request):
        coinflip_game = CoinFlipGame(user_id=request.user.id)
        return Response(coinflip_game.collect())

    @action(detail=False, methods=['post'], url_path='play')
    def play(self, request):
        params = request.data.copy()
        serializer = CoinFlipSerializer(data=params)
        serializer.is_valid(raise_exception=True)
        coinflip_game = CoinFlipGame(user_id=request.user.id)
        result = coinflip_game.play(bet=params['bet'], choice=params['choice'])

        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)


class BlackJackViewSet(ViewSet):
    queryset = None
    serializer_class = None

    view_permissions = {
        'start_game': {'admin': True, 'user': True},
        'play': {'admin': True, 'user': True},
    }

    def _game(self, user_id):
        return BlackJackGame(user_id=user_id)

    @action(detail=False, methods=['post'], url_path=r'(?P<action>hit|stand|double|split)')
    def play(self, request, action):
        game = self._game(user_id=request.user.id)
        result = getattr(game, action)()
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)

    @action(detail=False, methods=['post'], url_path='start-game')
    def start_game(self, request):
        params = request.data.copy()

        serializer = BlackJackSerializer(data=params)
        serializer.is_valid(raise_exception=True)

        result = self._game(user_id=request.user.id).create(bet=params['bet'])
        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)


class ThreeSevensViewSet(ViewSet):
    queryset = None
    serializer_class = None

    view_permissions = {
        'play': {'admin': True, 'user': True},
    }

    @action(detail=False, methods=['post'], url_path='play')
    def play(self, request):
        params = request.data.copy()

        serializer = ThreeSevensSerializer(data=params)
        serializer.is_valid(raise_exception=True)
        three_sevens_game = ThreeSevensGame(user_id=request.user.id)
        result = three_sevens_game.play(bet=params['bet'])

        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)


class SlotsViewSet(ViewSet):
    queryset = None
    serializer_class = None

    view_permissions = {
        'play': {'admin': True, 'user': True, 'anon': True},
    }

    @action(detail=False, methods=['post'], url_path='play')
    def play(self, request):
        params = request.data.copy()
        user = 'a3351425-7779-4ff2-a2d5-facd76dec70e'
        params['bet'] = 10
        # serializer = SlotSerializer(data=params)
        # serializer.is_valid(raise_exception=True)
        slots_game = SlotsGame(user_id=user)
        result = slots_game.play(bet=params['bet'])

        if 'error' in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)
