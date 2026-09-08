"""Callbacks that no state handler claimed.

PTB had two behaviours and they must both survive. A pattern-less fallback
inside the defect conversation absorbed any unmatched tap silently, and a
top-level InvalidCallbackData handler replaced the message with "this button
expired". The silent one won while a defect was in progress, because the
conversation was consulted first.

aiogram has no InvalidCallbackData — the payload is the string, so nothing is
ever unresolvable. What takes its place is three tiers, in this order:

1. a layout spacer, which must stay silent or tapping a blank button would
   wipe out the employee list;
2. a payload this build can still parse but no handler wanted — the old silent
   fallback, for out-of-order taps;
3. anything else. Two populations land here: buttons sent by the PTB build
   before cutover, whose payload was a bare UUID, and payloads whose shape
   changed across a deploy.
"""

import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError

from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)


async def noop_button(callback: CallbackQuery) -> None:
    """Absorb a spacer tap. Answering is what stops the client spinner."""
    await callback.answer()


async def unroutable_button(callback: CallbackQuery) -> None:
    """Absorb a valid payload that no handler in the current state wanted."""
    await callback.answer()


async def stale_button(callback: CallbackQuery, bot: Bot) -> None:
    """Tell the user the button is dead and take it off the screen.

    Edits by chat and message id rather than through callback.message, which by
    definition may be an InaccessibleMessage here — this handler exists for old
    messages.
    """
    await callback.answer()

    if callback.message is None:
        return

    try:
        await bot.edit_message_text(
            text=str(M.BUTTON_EXPIRED),
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
        )
    except TelegramAPIError:
        logger.debug("Could not replace a stale keyboard (message deleted or too old)")
