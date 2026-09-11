from datetime import timedelta

from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from django.conf import settings
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialWithJitterBackoff

FSM_TTL = timedelta(days=1)
FSM_SOCKET_TIMEOUT = 2.0
FSM_RETRIES = 2


def make_storage() -> RedisStorage:
    """Build Redis-backed FSM storage with bot-isolated keys to allow shared instances."""
    return RedisStorage(
        redis=Redis.from_url(
            settings.TELEGRAM_FSM_REDIS_URL,
            socket_timeout=FSM_SOCKET_TIMEOUT,
            socket_connect_timeout=FSM_SOCKET_TIMEOUT,
            retry=Retry(ExponentialWithJitterBackoff(cap=0.5, base=0.1), FSM_RETRIES),
        ),
        key_builder=DefaultKeyBuilder(with_bot_id=True),
        state_ttl=FSM_TTL,
        data_ttl=FSM_TTL,
    )
