"""Tests for the filters that have no aiogram built-in.

Both libraries are installed for the duration of the migration, so the
equivalence is checked against PTB directly on the same raw update rather than
against what we believe PTB does.
"""

import pytest
from aiogram.types import Message as AiogramMessage
from telegram import Message as PtbMessage
from telegram.ext import filters as ptb_filters

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


CASES = [
    pytest.param(_raw("plain text"), id="plain-text"),
    pytest.param(_raw("/start", [_command_entity(0, 6)]), id="command"),
    pytest.param(
        _raw("/start deep_link_token", [_command_entity(0, 6)]), id="command-with-args"
    ),
    pytest.param(
        _raw("call /help later", [_command_entity(5, 5)]), id="command-not-first"
    ),
    pytest.param(
        _raw("#tag /help", [{"type": "hashtag", "offset": 0, "length": 4}]),
        id="other-entity-first",
    ),
    pytest.param(_raw("60123456"), id="wagon-number"),
    pytest.param(_raw("worn/cracked weld"), id="text-containing-a-slash"),
    pytest.param(_raw(""), id="empty-text"),
]


@pytest.mark.parametrize("raw", CASES)
async def test_agrees_with_ptb_command_filter(raw):
    ptb_message = PtbMessage.de_json(raw, bot=None)
    aiogram_message = AiogramMessage.model_validate(raw)

    is_command_ptb = ptb_filters.COMMAND.filter(ptb_message)
    is_not_command_aiogram = await NotACommand()(aiogram_message)

    assert is_not_command_aiogram is not is_command_ptb


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
