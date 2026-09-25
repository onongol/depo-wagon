from typing import TYPE_CHECKING

from apps.bot.fsm import clear_defect_keys
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.utils.screens import answer_anew

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery


async def cancel_defect_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel the defect flow with the Cancel button on any step's keyboard."""
    await callback.answer()
    await clear_defect_keys(state)
    await state.set_state(None)
    await answer_anew(
        callback, text=str(M.DEFECT_CANCELLED), reply_markup=main_menu_keyboard()
    )


async def stale_callback(callback: CallbackQuery) -> None:
    """Silently absorb any callback no step in this flow claimed.

    Registered last inside the flow router, reproducing PTB's pattern-less
    fallback: while a defect is in progress an out-of-order tap dies quietly
    rather than getting the expired-button reply.
    """
    await callback.answer()
