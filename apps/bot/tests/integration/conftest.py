"""Fixtures for driving real Updates through a real Dispatcher."""

from itertools import count

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    Chat,
    Message,
    MessageEntity,
    PhotoSize,
    Update,
    User,
)

from apps.bot.dispatcher import make_dispatcher

from .mocked_bot import BOT_ID, make_mocked_bot

CHAT_ID = 12345
USER_ID = 12345

_update_ids = count(1)
_message_ids = count(1)


@pytest.fixture
def bot():
    return make_mocked_bot()


@pytest.fixture
def session(bot):
    return bot.session


@pytest.fixture
def storage():
    return MemoryStorage()


@pytest.fixture
def dp(storage):
    return make_dispatcher(storage)


@pytest.fixture
def state(storage) -> FSMContext:
    """The same key the dispatcher resolves for our synthetic updates."""
    return FSMContext(
        storage=storage,
        key=StorageKey(bot_id=BOT_ID, chat_id=CHAT_ID, user_id=USER_ID),
    )


def _user() -> User:
    return User(id=USER_ID, is_bot=False, first_name="Bat", username="bat")


def _chat() -> Chat:
    return Chat(id=CHAT_ID, type="private")


def make_message_update(text: str, *, command: bool = False) -> Update:
    entities = None
    if command:
        length = len(text.split(" ", 1)[0])
        entities = [MessageEntity(type="bot_command", offset=0, length=length)]

    return Update(
        update_id=next(_update_ids),
        message=Message(
            message_id=next(_message_ids),
            date=0,
            chat=_chat(),
            from_user=_user(),
            text=text,
            entities=entities,
        ),
    )


def make_photo_update(file_id: str, *, media_group_id: str | None = None) -> Update:
    return Update(
        update_id=next(_update_ids),
        message=Message(
            message_id=next(_message_ids),
            date=0,
            chat=_chat(),
            from_user=_user(),
            media_group_id=media_group_id,
            photo=[
                PhotoSize(
                    file_id=file_id,
                    file_unique_id=file_id,
                    width=100,
                    height=100,
                    file_size=1024,
                )
            ],
        ),
    )


def make_callback_update(data: str) -> Update:
    return Update(
        update_id=next(_update_ids),
        callback_query=CallbackQuery(
            id=str(next(_update_ids)),
            from_user=_user(),
            chat_instance="ci",
            data=data,
            message=Message(
                message_id=next(_message_ids),
                date=0,
                chat=_chat(),
                from_user=User(id=BOT_ID, is_bot=True, first_name="Bot"),
                text="previous",
            ),
        ),
    )
