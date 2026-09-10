"""Updates that no handler claimed.

A tap only reaches here once every registered filter has declined it, which is
the whole test: a payload whose shape changed across a deploy no longer matches
its own factory's filter, so it arrives alongside the buttons the PTB build
sent before cutover. Both are dead in the same way and both get told so rather
than left spinning.

Two things stay silent, and both are scoped rather than global. The layout
spacer is registered ahead of this one, or tapping a blank button would wipe
out the employee list. And a stray tap while a defect form is open never gets
this far — defect.cancel.stale_callback is registered last inside the flow
router under StateFilter(DefectSG), which is what keeps a mid-form misfire from
replacing the form with an expired-button notice.
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
