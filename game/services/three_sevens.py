from casino.redis.scripts import LuaScript
from casino.redis.client import redis_client
from django.db import transaction
from .provably_fair_game import ProvablyFairGame
from .base_func import log_game_result
from user.models import UserBalance, Currency
import json
import uuid


class ThreeSevensGame(ProvablyFairGame):
    _play_script = LuaScript.register(name='play', path='game/redis/lua/games/three_sevens')
    _game_code = '777'

    def __init__(self, user_id: uuid.UUID):
        super().__init__(user_id)
        self.r = redis_client
        self.user_id = user_id
        self._prefix = f"user:{user_id}"
        self.current_curency_code = self.r.get(f"{self._prefix}:current_currency").lower()

        self._keys = {
            'balance': f"{self._prefix}:balances",
            'pf_seeds': f"pf_seeds:{user_id}",
            'log_game': f"{self._prefix}:{self._game_code}_last_log"
        }

    def _keys_list(self):
        return [
            self._keys['balance'],
            self._keys['pf_seeds'],
            self._keys['log_game'],
        ]

    @log_game_result
    def play(self, bet: str):
        hash_hex, _, next_nonce, chain_drf_id = self._prepare_provably_fair(
            pf_key=self._keys['pf_seeds']
        )

        raw = self._play_script(
            keys=self._keys_list(),
            args=[
                'play',
                str(self.user_id),
                self.current_curency_code,
                bet,
                hash_hex,
                next_nonce,
                chain_drf_id,
            ]
        )

        result = json.loads(raw)

        if 'game_status' in result and result['game_status'] == 'win':
            self.set_balance_to_db(balance=result['balance'], currency_code=result['currency'])

        return result

    def set_balance_to_db(self, balance: str, currency_code: str):
        try:
            with transaction.atomic():
                currency = Currency.objects.get(code=currency_code)
                UserBalance.objects.filter(
                    user_fk=self.user_id,
                    currency_fk_id=currency.id
                ).update(amount=float(balance))
        except Exception as e:
            print(f"Balance sync failed: {e}")