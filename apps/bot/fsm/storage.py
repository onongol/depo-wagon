from datetime import timedelta

from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from django.conf import settings
from redis.asyncio import Redis

FSM_TTL = timedelta(days=1)


def make_storage() -> RedisStorage:
    """Build Redis-backed FSM storage with bot-isolated keys to allow shared instances."""
    return RedisStorage(
        redis=Redis.from_url(settings.TELEGRAM_FSM_REDIS_URL),
        key_builder=DefaultKeyBuilder(with_bot_id=True),
        state_ttl=FSM_TTL,
        data_ttl=FSM_TTL,
    )
