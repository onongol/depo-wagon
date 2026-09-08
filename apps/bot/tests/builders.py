"""Stand-ins for the aiogram objects handlers receive.

Not collected by pytest — the config only picks up *_tests.py.

Handlers take a Message or a CallbackQuery directly now, not an Update
wrapper, so these are shaped accordingly. Every method a handler awaits is an
AsyncMock, and both chat and message ids are set: the converted code addresses
messages by (chat_id, message_id) in several places.
"""

from unittest.mock import AsyncMock, MagicMock

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
    return callback


def make_command(args: str | None = None) -> MagicMock:
    """CommandObject, whose .args carries a /start deep-link payload."""
    command = MagicMock()
    command.args = args
    return command
