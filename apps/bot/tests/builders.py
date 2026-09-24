"""Stand-ins for the aiogram objects handlers receive.

Not collected by pytest — the config only picks up *_tests.py.

Handlers take a Message or a CallbackQuery directly now, not an Update
wrapper, so these are shaped accordingly. Every method a handler awaits is an
AsyncMock, and both chat and message ids are set: the converted code addresses
messages by (chat_id, message_id) in several places.
"""

from unittest.mock import AsyncMock, MagicMock

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText

CHAT_ID = 12345
USER_ID = 12345
MESSAGE_ID = 1


def make_message(text: str | None = None, *, user_id: int = USER_ID) -> MagicMock:
    message = MagicMock()
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    message.edit_text = AsyncMock()
    message.edit_reply_markup = AsyncMock()
    message.text = text
    message.message_id = MESSAGE_ID
    message.chat.id = CHAT_ID
    message.from_user.id = user_id
    return message


def make_callback(data: str | None = None, *, user_id: int = USER_ID) -> MagicMock:
    callback = MagicMock()
    callback.answer = AsyncMock()
    callback.data = data
    callback.from_user.id = user_id
    callback.message = make_message()
    callback.bot.edit_message_text = AsyncMock()
    callback.bot.send_message = AsyncMock()
    return callback


def make_command(args: str | None = None) -> MagicMock:
    """CommandObject, whose .args carries a /start deep-link payload."""
    command = MagicMock()
    command.args = args
    return command


def make_bad_request(message: str) -> TelegramBadRequest:
    """The error Telegram raises on an edit it refuses."""
    return TelegramBadRequest(
        method=EditMessageText(chat_id=1, message_id=1, text="x"), message=message
    )


def payloads(markup, factory) -> list[str]:
    """Callback payloads of one factory's buttons, in keyboard order."""
    return [
        btn.callback_data
        for row in markup.inline_keyboard
        for btn in row
        if btn.callback_data and btn.callback_data.startswith(factory.__prefix__ + ":")
    ]


def unpacked(markup, factory) -> list:
    return [factory.unpack(data) for data in payloads(markup, factory)]
