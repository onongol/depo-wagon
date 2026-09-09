"""Test storage that enforces what Redis enforces.

MemoryStorage keeps the dict by reference, so a lazy translation proxy or any
other non-JSON value passes in tests and only fails against real Redis. Every
handler test writes through this instead.
"""

import json
from typing import TYPE_CHECKING, Any

from aiogram.fsm.storage.memory import MemoryStorage

if TYPE_CHECKING:
    from aiogram.fsm.storage.base import StorageKey


class JSONMemoryStorage(MemoryStorage):
    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        await super().set_data(key, json.loads(json.dumps(data)))
