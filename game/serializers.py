from rest_framework import serializers
from .models import Game, GameCategory, GameConfig, GameHistory, ProvablyFairChain
from main.serializers import AttachmentSerializer
from user.serializers import OtherUserSerializer
from django.utils import timezone
from datetime import timedelta


class GameConfigSerializer(serializers.ModelSerializer):
    value = serializers.SerializerMethodField()

    class Meta:
        model = GameConfig
        fields = ['key', 'value']
        read_only_fields = fields

    def get_value(self, obj):
        try:
            return float(obj.value)
        except ValueError:
            return obj.value

class GameSerializer(serializers.ModelSerializer):
    image_fk = AttachmentSerializer(read_only=True)
    # configs = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            'id',
            'name',
            'slug',
            'image_fk',
            'code',
            'order',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    # def get_configs(self, obj):
    #     return GameConfigSerializer(obj.config.all(), many=True).data


class GameCategorySerializer(serializers.ModelSerializer):
    games = GameSerializer(source='game_set', many=True, read_only=True)

    class Meta:
        model = GameCategory
        fields = [
            'id',
            'name',
            'slug',
            'order',
            'games',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

class BetCheckSerializer(serializers.Serializer):
    bet = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_bet(self, value):
        if value <= 0:
            raise serializers.ValidationError('The bet must be positive.')
        return value


class CoinFlipSerializer(BetCheckSerializer):
    choice = serializers.IntegerField(min_value=0, max_value=1)


class BlackJackSerializer(BetCheckSerializer):
    pass


class ThreeSevensSerializer(BetCheckSerializer):
    pass

class SlotSerializer(BetCheckSerializer):
    pass

class ProvablyFairChainSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProvablyFairChain
        fields = [
            'id',
            'user_fk',
            'server_seed',
            'server_seed_hash',
            'client_seed',
            'revealed_at',
            'created_at',
        ]

        read_only_fields = fields


class GameHistoryStatsSerializer(serializers.ModelSerializer):
    user_fk = OtherUserSerializer(read_only=True)

    class Meta:
        model = GameHistory
        fields = [
            'id',
            'user_fk',
            'bet_amount',
            'payout',
            'multiplier',
            'created_at',
        ]

        read_only_fields = fields


class GameHistoryTop10Serializer(serializers.ModelSerializer):
    user_fk = OtherUserSerializer(read_only=True)
    game_name = serializers.CharField(source='game_fk.name', read_only=True)
    game_code = serializers.CharField(source='game_fk.code', read_only=True)

    class Meta:
        model = GameHistory
        fields = [
            'id',
            'user_fk',
            'game_fk',
            'game_name',
            'game_code',
            'bet_amount',
            'payout',
            'multiplier',
            'created_at',
        ]

        read_only_fields = fields


class GameHistorySerializer(serializers.ModelSerializer):
    pf_chain_fk = serializers.SerializerMethodField()
    nonce = serializers.SerializerMethodField()

    class Meta:
        model = GameHistory
        fields = [
            'id',
            'user_fk',
            'game_fk',
            'pf_chain_fk',
            'nonce',
            'bet_amount',
            'payout',
            'multiplier',
            'game_status',
            'game_data',
            'created_at',
        ]

        read_only_fields = fields

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        if instance.created_at <= timezone.now() - timedelta(days=1):
            ret['pf_chain_fk'] = instance.pf_chain_fk_id
            ret['nonce'] = instance.nonce
        else:
            ret['pf_chain_fk'] = None
            ret['nonce'] = None
        return ret
