from casino.redis.client import redis_client
import json
import secrets
import hashlib
import uuid
from casino.redis.scripts import LuaScript

get_balance = LuaScript.register('balance/get')

def get_user_current_currency(user_id: uuid.UUID):
    key_currency = f"user:{user_id}:current_currency"
    return redis_client.get(key_currency)

def get_user_balances(user_id: uuid) -> dict:
    key_balance = f"user:{user_id}:balances"
    key_currency = f"user:{user_id}:current_currency"

    raw = get_balance(keys=[key_balance, key_currency])
    if not raw:
        raw = '{}'

    data = json.loads(raw)

    return data

def generate_seeds():
    server_seed = secrets.token_hex(64)
    server_seed_hash = hashlib.sha512(server_seed.encode()).hexdigest()
    client_seed = secrets.token_hex(32)
    nonce = 0

    return {
        'server_seed': server_seed,
        'server_seed_hash': server_seed_hash,
        'client_seed': client_seed,
        'nonce': nonce
    }

def set_user_info_to_redis(user):
    key = f"user:{user.id}:info"

    if redis_client.exists(key):
        return

    user_data = {
        'pk': str(user.pk),
        'username': user.username,
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'email': user.email or '',
    }

    redis_client.set(key, json.dumps(user_data), ex=604800)

def ensure_user_balances(user):
    from .models import UserBalance

    user_id = user.id
    balances_key = f"user:{user_id}:balances"
    currency_key = f"user:{user_id}:current_currency"

    data = redis_client.get(balances_key)
    current_currency = redis_client.get(currency_key)

    if data:
        return json.loads(data)

    qs = UserBalance.objects.filter(user_fk=user).select_related('currency_fk').values_list(
        'currency_fk__code',
        'amount',
        'currency_fk__balance_decimal_places',
        'currency_fk__payout_decimal_places',
    )

    balances = {}
    for code, amount, balance_decimal_places, payout_decimal_places in qs:
        balances[code] = {
            'amount': str(amount or '0'),
            'balance_decimal_places': balance_decimal_places,
            'payout_decimal_places': payout_decimal_places,
        }

    pipe = redis_client.pipeline()
    pipe.set(balances_key, json.dumps(balances))

    if not current_currency:
        pipe.set(currency_key, 'usd')

    pipe.execute()

    return balances
