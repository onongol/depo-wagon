"""Shared fixtures for the bot tests.

Two sets live here during the migration. `state` and the aiogram builders are
for converted handlers; `mock_update`/`mock_context` serve the flows still on
PTB and go with the last of them.

`state` is a real FSMContext over MemoryStorage rather than a mock, so
get_state and get_data behave exactly as they will against Redis — including
the part that catches missed saves, where a loaded DefectData is a detached
copy.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage

USER_ID = 12345
CHAT_ID = 12345


@pytest.fixture
def state() -> FSMContext:
    return FSMContext(
        storage=MemoryStorage(),
        key=StorageKey(bot_id=42, chat_id=CHAT_ID, user_id=USER_ID),
    )


@pytest.fixture
def message() -> MagicMock:
    from apps.bot.tests.builders import make_message

    return make_message()


@pytest.fixture
def callback() -> MagicMock:
    from apps.bot.tests.builders import make_callback

    return make_callback()


@pytest.fixture
def bot() -> MagicMock:
    """Stand-in for the injected Bot. Every API method is awaitable."""
    return MagicMock(
        send_message=AsyncMock(),
        edit_message_text=AsyncMock(),
        edit_message_reply_markup=AsyncMock(),
        copy_message=AsyncMock(),
    )


@pytest.fixture
def mock_update():
    """PTB-era fixture. Remove with the last PTB handler."""
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    update.effective_user.id = USER_ID
    return update


@pytest.fixture
def mock_context():
    """PTB-era fixture. Remove with the last PTB handler."""
    context = MagicMock()
    context.user_data = {}
    return context
