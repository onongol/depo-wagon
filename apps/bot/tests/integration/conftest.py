"""Fixtures for driving real Updates through a real Dispatcher."""

import logging
from itertools import count
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import (
    CallbackQuery,
    Chat,
    InaccessibleMessage,
    Message,
    MessageEntity,
    PhotoSize,
    Update,
    User,
)

from apps.bot.dispatcher import make_dispatcher
from apps.bot.tests.storage import JSONMemoryStorage

from .mocked_bot import BOT_ID, make_mocked_bot

CHAT_ID = 12345
USER_ID = 12345

_update_ids = count(1)
_message_ids = count(1)


@pytest.fixture(autouse=True)
def _no_connection_cleanup():
    """pytest-django blocks the touch once an earlier test left a connection open."""
    with patch("apps.bot.middlewares.db.close_old_connections"):
        yield


class _Crashes(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture(autouse=True)
def _no_swallowed_crash():
    """error_handler turns a crash into a polite reply; a test must not pass on it.

    A class whose tests break a handler on purpose overrides this with a no-op.
    """
    crashes = _Crashes()
    error_log = logging.getLogger("apps.bot.errors")
    error_log.addHandler(crashes)
    yield
    error_log.removeHandler(crashes)

    if crashes.records:
        pytest.fail(
            "A handler crashed and error_handler swallowed it.\n"
            + logging.Formatter().formatException(crashes.records[0].exc_info),
            pytrace=False,
        )


@pytest.fixture
def bot():
    return make_mocked_bot()


@pytest.fixture
def session(bot):
    return bot.session


@pytest.fixture
def storage():
    return JSONMemoryStorage()


@pytest.fixture
def dp(storage):
    return make_dispatcher(storage, SimpleEventIsolation())


@pytest.fixture
def state(storage) -> FSMContext:
    """The same key the dispatcher resolves for our synthetic updates."""
    return FSMContext(
        storage=storage,
        key=StorageKey(bot_id=BOT_ID, chat_id=CHAT_ID, user_id=USER_ID),
    )


def as_employee(employee):
    """Answer the dispatcher's employee lookup with this employee."""
    return patch(
        "apps.bot.middlewares.employee.services.get_employee_by_telegram_id",
        AsyncMock(return_value=employee),
    )


def _user() -> User:
    return User(id=USER_ID, is_bot=False, first_name="Bat", username="bat")


def _chat(chat_type: str = "private") -> Chat:
    return Chat(id=CHAT_ID, type=chat_type)


def make_message_update(
    text: str, *, command: bool = False, chat_type: str = "private"
) -> Update:
    entities = None
    if command:
        length = len(text.split(" ", 1)[0])
        entities = [MessageEntity(type="bot_command", offset=0, length=length)]

    return Update(
        update_id=next(_update_ids),
        message=Message(
            message_id=next(_message_ids),
            date=0,
            chat=_chat(chat_type),
            from_user=_user(),
            text=text,
            entities=entities,
        ),
    )


def make_photo_update(
    file_id: str, *, media_group_id: str | None = None, message_id: int | None = None
) -> Update:
    return Update(
        update_id=next(_update_ids),
        message=Message(
            message_id=next(_message_ids) if message_id is None else message_id,
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


def make_callback_update(
    data: str, *, inaccessible: bool = False, chat_type: str = "private"
) -> Update:
    """A button tap; inaccessible puts it on a message the bot can no longer see."""
    message_id = next(_message_ids)
    if inaccessible:
        message = InaccessibleMessage(
            chat=_chat(chat_type), message_id=message_id, date=0
        )
    else:
        message = Message(
            message_id=message_id,
            date=0,
            chat=_chat(chat_type),
            from_user=User(id=BOT_ID, is_bot=True, first_name="Bot"),
            text="previous",
        )

    return Update(
        update_id=next(_update_ids),
        callback_query=CallbackQuery(
            id=str(next(_update_ids)),
            from_user=_user(),
            chat_instance="ci",
            data=data,
            message=message,
        ),
    )
