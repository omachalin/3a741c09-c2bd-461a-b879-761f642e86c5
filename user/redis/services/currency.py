from casino.redis.scripts import LuaScript
from user.models import Currency
from functools import lru_cache
import json

class CurrencyService():
    _change_currency_script = LuaScript.register(name='change_currency', path='user/redis/lua')

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.currency_key = f"user:{user_id}:current_currency"

    @staticmethod
    @lru_cache(maxsize=100)
    def currency_exists(code: str) -> bool:
        return Currency.objects.filter(code=code).exists()

    def change_currency(self, new_currency_code: str):
        if not self.currency_exists(new_currency_code):
            raise ValueError(f"Currency with code '{new_currency_code}' does not exist.")

        raw = self._change_currency_script(
            keys=[self.currency_key],
            args=[new_currency_code.lower(), str(self.user_id)]
        )

        return json.loads(raw)
