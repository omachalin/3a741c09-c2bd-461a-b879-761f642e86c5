import uuid
import hmac
import hashlib
from django.utils import timezone
from casino.redis.client import redis_client
from user.func import generate_seeds
from game.models import ProvablyFairChain
from django.conf import settings


class ProvablyFairGame:
    REDIS_TTL = 86400

    def __init__(self, user_id: uuid.UUID):
        if not user_id:
            raise ValueError("User ID is required for Provably Fair Game")

        self.user_id = user_id
        self.key = f"pf_seeds:{user_id}"
        self._ensure_fair_state()

    def _ensure_fair_state(self):
        if not redis_client.exists(self.key):
            self._rotate_server_seed()

    def _rotate_server_seed(self):
        ProvablyFairChain.objects.filter(
            user_fk_id=self.user_id,
            revealed_at__isnull=True
        ).update(
            revealed_at=timezone.now()
        )

        seeds = generate_seeds()

        new_chain = ProvablyFairChain.objects.create(
            user_fk_id=self.user_id,
            server_seed=seeds['server_seed'],
            server_seed_hash=seeds['server_seed_hash'],
            client_seed=seeds['client_seed'],
        )

        redis_client.hset(self.key, mapping={
            'server_seed': seeds['server_seed'],
            'server_seed_hash': seeds['server_seed_hash'],
            'client_seed': seeds['client_seed'],
            'nonce': seeds['nonce'],
            'chain_drf_id': str(new_chain.id)
        })

        redis_client.expire(self.key, self.REDIS_TTL)

    def _prepare_provably_fair(self, pf_key):
        pf_data = redis_client.hmget(pf_key, 'server_seed', 'client_seed', 'nonce', 'chain_drf_id')
        server_seed, client_seed, nonce, chain_drf_id = pf_data

        if not server_seed or not client_seed:
            raise ValueError("Provably fair seeds missing")

        nonce = nonce if nonce else '0'
        next_nonce = str(int(nonce) + 1)

        message = f"{client_seed}:{nonce}"
        hash_hex = hmac.new(
            server_seed.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return hash_hex, nonce, next_nonce, chain_drf_id
