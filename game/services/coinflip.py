from casino.redis.scripts import LuaScript
from casino.redis.client import redis_client
from typing import Literal
from user.models import UserBalance, Currency
from django.db import transaction
from .provably_fair_game import ProvablyFairGame
from .base_func import log_game_result
import json
import uuid


class CoinFlipGame(ProvablyFairGame):
    _game_code = 'coin_flip'
    _play_script = LuaScript.register(name='coinflip_play', path='game/redis/lua/games/coinflip')
    _collect_script = LuaScript.register(name='coinflip_collect', path='game/redis/lua/games/coinflip')

    def __init__(self, user_id: uuid.UUID):
        super().__init__(user_id)
        self.user_id = user_id
        self.r = redis_client
        self._prefix = f"user:{user_id}"
        self.pf_key = f"pf_seeds:{user_id}"
        self.current_curency_code = self.r.get(f"{self._prefix}:current_currency").lower()

        self._keys = {
            'balance': f"{self._prefix}:balances",
            'streak': f"{self._prefix}:coinflip_streak",
            'pending': f"{self._prefix}:coinflip_pending",
            'pf': self.pf_key,
            'start_bet': f"{self._prefix}:start_bet",
        }

    def _keys_list(self):
        return [
            self._keys['balance'],
            self._keys['streak'],
            self._keys['pending'],
            self._keys['pf'],
            self._keys['start_bet'],
        ]

    @log_game_result
    def play(self, bet: str, choice: Literal[0, 1]) -> dict:
        hash_hex, _, next_nonce, chain_drf_id = self._prepare_provably_fair(pf_key=self._keys['pf'])

        raw = self._play_script(
            keys=self._keys_list(),
            args=[
                self.current_curency_code,
                bet,
                str(choice),
                hash_hex,
                next_nonce,
                str(self.user_id),
                chain_drf_id,
                self._game_code,
            ]
        )

        return json.loads(raw)

    @log_game_result
    def collect(self) -> dict:
        raw = self._collect_script(
            keys=self._keys_list(),
            args=[
                self.current_curency_code,
                str(self.user_id),
                self._game_code,
            ]
        )
        result = json.loads(raw)

        if 'error' in result:
            return result

        self.set_balance_to_db(balance=result['balance'])
        return result

    def set_balance_to_db(self, balance: str):
        try:
            with transaction.atomic():
                currency = Currency.objects.get(code=self.current_curency_code)
                UserBalance.objects.filter(
                    user_fk=self.user_id,
                    currency_fk_id=currency.id
                ).update(amount=float(balance))
        except Exception as e:
            print(f"Balance sync failed: {e}")
