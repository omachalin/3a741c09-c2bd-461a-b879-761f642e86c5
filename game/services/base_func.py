from game.tasks import save_game_async
from functools import lru_cache
from functools import wraps
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime


def get_game_config(code: str) -> dict:
    from casino.redis.client import redis_client
    cache_key = f"game_config:{code}"

    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    from game.models import GameConfig
    configs = GameConfig.objects.filter(
        game_fk__code=code,
        is_public=True
    ).values_list('key', 'value')

    cfg_dict = {k: v for k, v in configs}

    redis_client.set(cache_key, json.dumps(cfg_dict))

    return cfg_dict

@lru_cache(maxsize=128)
def get_game(code: str):
    from game.models import Game
    return Game.objects.values("id", 'name').get(code=code)

@lru_cache(maxsize=128)
def get_currency_id(code: str):
    from user.models import Currency
    return Currency.objects.values_list("id", flat=True).get(code=code)

def get_user_info(user_id, redis):
    key = f"user:{str(user_id)}:info"
    try:
        data = json.loads(redis.get(key))
        return {
            'id': user_id,
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
        }
    except Exception as e:
        print(f"Failed to get user info for {user_id}: {e}")
        return {}

def send_game_notification(game_code, game_name, currency_code, log_data, redis):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        'games',
        {
            'type': 'game_notification',
            'data': {
                'game_name': game_name,
                'game_code': str(game_code),
                'bet': str(log_data.get('bet_amount', 0)),
                'payout': log_data.get('payout', 0),
                'currency': currency_code,
                'multiplier': log_data.get('multiplier', 0),
                'updated_at': datetime.utcnow().isoformat(),
                'user': get_user_info(user_id=log_data.get('user_fk_id'), redis=redis),
                'created_at': datetime.now().isoformat(),
            }
        }
    )

def log_game_result(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)

        if result.get('error'):
            return result

        game_code = getattr(self, '_game_code', 'unknown')
        current_curency_code = getattr(self, 'current_curency_code', 'unknown')

        log_key = f"user:{str(self.user_id)}:{game_code}_last_log"
        raw_log = self.r.get(log_key)

        if raw_log:
            try:
                log_data = json.loads(raw_log)

                if log_data.get('game_status') == 'ongoing':
                    return result

                game = get_game(code=game_code)
                log_data['game_fk_id'] = game['id']

                log_data['currency_fk_id'] = get_currency_id(code=current_curency_code)

                save_game_async.delay(log_data)
                send_game_notification(
                    game_code=game_code,
                    game_name=game['name'],
                    currency_code=current_curency_code,
                    log_data=log_data,
                    redis=self.r
                )

            except Exception as e:
                print(f"[log_game_result:{game_code}] Failed to save: {e}")

        return result
    return wrapper
