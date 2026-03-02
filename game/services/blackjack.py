from casino.redis.scripts import LuaScript
from casino.redis.client import redis_client
from django.db import transaction
from .provably_fair_game import ProvablyFairGame
from .base_func import log_game_result
import json
import uuid


class BlackJackGame(ProvablyFairGame):
    _play_script = LuaScript.register(name='play', path='game/redis/lua/games/blackjack')
    _game_code = 'blackjack'

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

    def build_dealer_response(self, data):
        if 'error' in data:
            return data

        if data['dealer']['status_game'] == 'ongoing':
            data['dealer']['hand'] = [data['dealer']['hand'][0], 'hidden']
        return {
            'bet': data['bet'],
            'currency': data['currency'],
            'balance': data['balance'],
            'game': {
                'player': data['player'],
                'dealer': data['dealer'],
            }
        }

    @log_game_result
    def stand(self):
        raw = self._play_script(
            keys=self._keys_list(),
            args=[
                'stand',
                str(self.user_id),
                self.current_curency_code,
            ]
        )

        return self.build_dealer_response(data=json.loads(raw))

    @log_game_result
    def hit(self):
        raw = self._play_script(
            keys=self._keys_list(),
            args=[
                'hit',
                str(self.user_id),
                self.current_curency_code,
            ]
        )

        return self.build_dealer_response(data=json.loads(raw))

    @log_game_result
    def create(self, bet: str):
        hash_hex, _, next_nonce, chain_drf_id = self._prepare_provably_fair(
            pf_key=self._keys['pf_seeds']
        )

        raw = self._play_script(
            keys=self._keys_list(),
            args=[
                'create',
                str(self.user_id),
                self.current_curency_code,
                bet,
                hash_hex,
                next_nonce,
                chain_drf_id,
            ]
        )

        return self.build_dealer_response(data=json.loads(raw))

    @log_game_result
    def double(self):
        raw = self._play_script(
            keys=self._keys_list(),
            args=[
                'double',
                str(self.user_id),
                self.current_curency_code,
            ]
        )

        return self.build_dealer_response(data=json.loads(raw))

    def split(self):
        raw = self._play_script(
            keys=self._keys_list(),
            args=[
                'split',
                str(self.user_id),
                self.current_curency_code,
            ]
        )

        return self.build_dealer_response(data=json.loads(raw))
