from datetime import timedelta

from aiogram.fsm.storage.redis import (
    DefaultKeyBuilder,
    RedisEventIsolation,
    RedisStorage,
)
from django.conf import settings
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialWithJitterBackoff

FSM_TTL = timedelta(days=1)
FSM_SOCKET_TIMEOUT = 2.0
FSM_RETRIES = 2
FSM_LOCK_TIMEOUT = 90.0

# Scenes keep their history under a destiny of its own, which the builder
# refuses without with_destiny
FSM_KEY_BUILDER = DefaultKeyBuilder(with_bot_id=True, with_destiny=True)


def make_storage() -> RedisStorage:
    """Build Redis-backed FSM storage with bot-isolated keys to allow shared instances."""
    return RedisStorage(
        redis=Redis.from_url(
            settings.TELEGRAM_FSM_REDIS_URL,
            socket_timeout=FSM_SOCKET_TIMEOUT,
            socket_connect_timeout=FSM_SOCKET_TIMEOUT,
            retry=Retry(ExponentialWithJitterBackoff(cap=0.5, base=0.1), FSM_RETRIES),
        ),
        key_builder=FSM_KEY_BUILDER,
        state_ttl=FSM_TTL,
        data_ttl=FSM_TTL,
    )


def make_isolation(storage: RedisStorage) -> RedisEventIsolation:
    """Build the per-user event lock over the storage's own connection and keys."""
    return storage.create_isolation(lock_kwargs={"timeout": FSM_LOCK_TIMEOUT})
