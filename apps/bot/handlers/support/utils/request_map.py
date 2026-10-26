from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram.fsm.storage.redis import RedisStorage

# Relayed group message -> asking user's chat id, on the FSM storage's Redis:
# noeviction + AOF, unlike the cache. Message ids repeat across chats.
SUPPORT_MAP_PREFIX = "support_request:"
SUPPORT_MAP_TTL = 30 * 24 * 3600  # 30 days


def _map_key(chat_id: int, message_id: int) -> str:
    return f"{SUPPORT_MAP_PREFIX}{chat_id}:{message_id}"


async def remember_request(
    storage: RedisStorage, chat_id: int, message_id: int, user_id: int
) -> None:
    """Link a relayed group message to the user who sent the request."""
    await storage.redis.set(_map_key(chat_id, message_id), user_id, ex=SUPPORT_MAP_TTL)


async def lookup_request(
    storage: RedisStorage, chat_id: int, message_id: int
) -> int | None:
    """Return the user id behind a relayed message, or None if unknown/expired."""
    user_id = await storage.redis.get(_map_key(chat_id, message_id))
    return None if user_id is None else int(user_id)
