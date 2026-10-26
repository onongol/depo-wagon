"""Test storage that enforces what Redis enforces.

MemoryStorage keeps the dict by reference, so a lazy translation proxy or any
other non-JSON value passes in tests and only fails against real Redis. It also
never builds a key, so a key the production builder refuses passes too. Every
handler test goes through this instead.
"""

import json
from typing import TYPE_CHECKING, Any

from aiogram.fsm.storage.memory import MemoryStorage

from apps.bot.fsm.storage import FSM_KEY_BUILDER

if TYPE_CHECKING:
    from aiogram.fsm.state import State
    from aiogram.fsm.storage.base import StorageKey


class _BytesRedis:
    """The commands handlers run on RedisStorage.redis; values come back as bytes."""

    def __init__(self) -> None:
        self._values: dict[str, bytes] = {}

    async def set(self, name: str, value: Any, ex: int | None = None) -> None:
        self._values[name] = str(value).encode()

    async def get(self, name: str) -> bytes | None:
        return self._values.get(name)


class JSONMemoryStorage(MemoryStorage):
    def __init__(self) -> None:
        super().__init__()
        self.redis = _BytesRedis()

    async def set_state(
        self, key: StorageKey, state: State | str | None = None
    ) -> None:
        FSM_KEY_BUILDER.build(key, "state")
        await super().set_state(key, state)

    async def get_state(self, key: StorageKey) -> str | None:
        FSM_KEY_BUILDER.build(key, "state")
        return await super().get_state(key)

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        FSM_KEY_BUILDER.build(key, "data")
        await super().set_data(key, json.loads(json.dumps(data)))

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        FSM_KEY_BUILDER.build(key, "data")
        return await super().get_data(key)
