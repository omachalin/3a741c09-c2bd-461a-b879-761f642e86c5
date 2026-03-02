from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import User, UserBalance
from casino.redis.client import redis_client


class OtherUserSerializer(serializers.ModelSerializer):
    avatar = serializers.CharField(source='avatar_fk.file', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'avatar', 'date_joined']
        read_only_fields = fields


class UserBalanceSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source='currency_fk.code', read_only=True)
    icon = serializers.CharField(source='currency_fk.icon', read_only=True)

    class Meta:
        model = UserBalance
        fields = ['currency_code', 'amount', 'icon']
        read_only_fields = fields


class SelfUserSerializer(serializers.ModelSerializer):
    balances = serializers.SerializerMethodField()
    current_currency = serializers.SerializerMethodField()
    avatar = serializers.CharField(source='avatar_fk.file', read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'avatar',
            'balances',
            'current_currency',
            'date_joined'
        ]
        read_only_fields = fields

    def get_current_currency(self, obj) -> str:
        raw = redis_client.get(f"user:{str(obj.id)}:current_currency")
        return raw if raw else 'usd'

    def get_balances(self, obj):
        from user.func import ensure_user_balances
        return ensure_user_balances(obj)


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'username'

    def validate(self, attrs):
        identifier = attrs.get('username')
        password = attrs.get('password')

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=identifier)
            except User.DoesNotExist:
                raise serializers.ValidationError('No user with this username/email.')

        if not user.check_password(password):
            raise serializers.ValidationError('Incorrect credentials.')

        data = super().validate({'username': user.username, 'password': password})
        user_data = SelfUserSerializer(user).data
        data.update({'user': user_data})

        return data
