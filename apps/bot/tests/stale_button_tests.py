from unittest.mock import AsyncMock, MagicMock

from apps.bot.handlers.common.stale import stale_button
from apps.bot.messages import BotMessages as M


def _make_cb_update():
    update = MagicMock()
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    return update


class TestStaleButton:
    async def test_answers_the_query(self, mock_context):
        update = _make_cb_update()
        await stale_button(update, mock_context)
        update.callback_query.answer.assert_awaited_once()

    async def test_replaces_the_message_with_an_explanation(self, mock_context):
        update = _make_cb_update()
        await stale_button(update, mock_context)
        assert update.callback_query.edit_message_text.await_args.args[0] == str(
            M.BUTTON_EXPIRED
        )

    async def test_an_uneditable_message_does_not_raise(self, mock_context):
        update = _make_cb_update()
        update.callback_query.edit_message_text = AsyncMock(
            side_effect=Exception("message is too old")
        )
        await stale_button(update, mock_context)
        update.callback_query.answer.assert_awaited_once()
