from typing import TYPE_CHECKING

from apps.bot.fsm import clear_defect_keys
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message


async def cancel_defect_command(message: Message, state: FSMContext) -> None:
    """Cancel the defect flow with /cancel."""
    await clear_defect_keys(state)
    await state.set_state(None)
    await message.answer(str(M.DEFECT_CANCELLED))


async def cancel_defect_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel the defect flow with the Cancel button on any step's keyboard."""
    await callback.answer()
    await clear_defect_keys(state)
    await state.set_state(None)
    await callback.message.edit_text(str(M.DEFECT_CANCELLED))


async def stale_callback(callback: CallbackQuery) -> None:
    """Silently absorb any callback no step in this flow claimed.

    Registered last inside the flow router, reproducing PTB's pattern-less
    fallback: while a defect is in progress an out-of-order tap dies quietly
    rather than getting the expired-button reply.
    """
    await callback.answer()
