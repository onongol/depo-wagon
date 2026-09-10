"""Updates that no state handler claimed.

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

import inspect
import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.state import StatesGroup

from apps.bot import states
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)

# Read off the module rather than listed, so a new group is covered on sight.
KNOWN_STATES = frozenset(
    name
    for _, group in inspect.getmembers(states, inspect.isclass)
    if issubclass(group, StatesGroup) and group is not StatesGroup
    for name in group.__all_states_names__
)


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


async def unhandled_message(message: Message, state: FSMContext) -> None:
    """Answer a private message no router claimed, instead of going quiet.

    Silent while a state this build knows is live: the step is mid-flow and the
    user sent the wrong content type, so its own prompt still stands and the
    form must survive. Silence is only wrong once nothing is waiting — an
    expired FSM key, or a state string left by an older build.
    """
    current = await state.get_state()

    if current in KNOWN_STATES:
        return

    if current is not None:
        logger.warning("Clearing an FSM state this build does not know: %s", current)
        await state.clear()

    await message.answer(str(M.UNHANDLED_MESSAGE), parse_mode=M.PARSE_MODE)
