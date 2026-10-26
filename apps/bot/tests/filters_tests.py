"""Tests for the filters that have no aiogram built-in.

The semantics below are PTB's, not a guess: while both libraries were installed
these cases were asserted to be exact inverses of filters.COMMAND on the same
raw update. PTB is gone now, so the expectations stand on their own.
"""

from aiogram.types import Message as AiogramMessage

from apps.bot.filters import NotACommand


def _raw(text: str, entities: list[dict] | None = None) -> dict:
    return {
        "message_id": 1,
        "date": 0,
        "chat": {"id": 1, "type": "private"},
        "from": {"id": 1, "is_bot": False, "first_name": "T"},
        "text": text,
        "entities": entities or [],
    }


def _command_entity(offset: int, length: int) -> dict:
    return {"type": "bot_command", "offset": offset, "length": length}


class TestNotACommand:
    async def test_accepts_text_without_entities(self):
        assert await NotACommand()(AiogramMessage.model_validate(_raw("hello")))

    async def test_rejects_a_leading_command(self):
        message = AiogramMessage.model_validate(
            _raw("/cancel", [_command_entity(0, 7)])
        )

        assert not await NotACommand()(message)

    async def test_accepts_a_command_that_is_not_first(self):
        """A description may mention a slash-word without being a command."""
        message = AiogramMessage.model_validate(
            _raw("see /help", [_command_entity(4, 5)])
        )

        assert await NotACommand()(message)

    async def test_accepts_when_another_entity_comes_first(self):
        message = AiogramMessage.model_validate(
            _raw(
                "#tag /help",
                [
                    {"type": "hashtag", "offset": 0, "length": 4},
                    _command_entity(5, 5),
                ],
            )
        )

        assert await NotACommand()(message)

    async def test_accepts_a_photo_message_with_no_text(self):
        message = AiogramMessage.model_validate(
            {
                "message_id": 1,
                "date": 0,
                "chat": {"id": 1, "type": "private"},
                "photo": [
                    {
                        "file_id": "a",
                        "file_unique_id": "b",
                        "width": 1,
                        "height": 1,
                    }
                ],
            }
        )

        assert await NotACommand()(message)
