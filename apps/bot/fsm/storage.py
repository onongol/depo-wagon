"""Redis-backed FSM storage."""

from datetime import timedelta

from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage
from django.conf import settings
from redis.asyncio import Redis

# RedisStorage sets no expiry of its own. The FSM lives on the same instance as
# the Celery queue, which runs noeviction, so an abandoned defect form would sit
# there forever and eventually stop Celery from accepting tasks. A day is also
# closer to the current behaviour, where state dies with the process.
FSM_TTL = timedelta(days=1)


def make_storage() -> RedisStorage:
    """Build the FSM storage.

    with_bot_id keys the state by bot as well as chat and user, so a second
    token — a staging bot — can share the instance without colliding.
    """
    return RedisStorage(
        redis=Redis.from_url(settings.TELEGRAM_FSM_REDIS_URL),
        key_builder=DefaultKeyBuilder(with_bot_id=True),
        state_ttl=FSM_TTL,
        data_ttl=FSM_TTL,
    )
