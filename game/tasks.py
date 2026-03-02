from celery import shared_task
from django.db import OperationalError, DatabaseError
from .models import GameHistory
import logging
logger = logging.getLogger(__name__)

@shared_task(
    bind=True,

    autoretry_for=(OperationalError, DatabaseError),
    retry_kwargs={'max_retries': 5, 'countdown': 5},

    acks_late=True,

    reject_on_worker_lost=True,
)
def save_game_async(self, game_data: dict):
    try:
        allowed_fields = { f.name for f in GameHistory._meta.concrete_fields }
        allowed_fields.update({'user_fk_id', 'pf_chain_fk_id', 'currency_fk_id', 'game_fk_id'})

        filtered_data = {
            k: v for k, v in game_data.items()
            if k in allowed_fields
        }

        obj = GameHistory.objects.create(**filtered_data)
        return obj.id

    except Exception as e:
        print("Failed to create GameHistory:", e)

        import traceback
        traceback.print_exc()
        raise
