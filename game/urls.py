from rest_framework import routers
from .views import (
    GameViewSet, GameCategoryViewSet, CoinFlipViewSet, GameHistoryViewSet, BlackJackViewSet, StatsViewSet,
    GameConfig, ThreeSevensViewSet, SlotsViewSet)

urlpatterns = [

]

router = routers.DefaultRouter()
router.register(r'game', GameViewSet, basename='game')
router.register(r'category', GameCategoryViewSet, basename='game-category')
router.register(r'coinflip', CoinFlipViewSet, basename='coinflip')
router.register(r'blackjack', BlackJackViewSet, basename='blackjack')
router.register(r'three-sevens', ThreeSevensViewSet, basename='three-sevens')
router.register(r'game-history', GameHistoryViewSet, basename='game-history')
router.register(r'config', GameConfig, basename='config')
router.register(r'stats', StatsViewSet, basename='stats')
router.register(r'slot-fruit', SlotsViewSet, basename='slot-fruit')

urlpatterns += router.urls
