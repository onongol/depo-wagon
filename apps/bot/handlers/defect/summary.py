from typing import TYPE_CHECKING

from apps.bot.constants import UD_EDITING
from apps.bot.fsm import drop_keys
from apps.bot.states import DefectSG

from .text import build_summary_text

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext

    from apps.bot.user_data import DefectData


async def show_summary(
    send: Callable[..., Awaitable], state: FSMContext, defect: DefectData
) -> None:
    """Render the review screen and enter the confirm state.

    Takes the send callable rather than the event: six handlers converge here,
    some from a text message (a new message) and some from a button (an edit in
    place), which is what PTB expressed by branching on update.callback_query.
    """
    from apps.bot.keyboards.confirm import confirm_keyboard

    await drop_keys(state, UD_EDITING)

    await send(
        **build_summary_text(defect).as_kwargs(),
        reply_markup=confirm_keyboard(defect),
    )
    await state.set_state(DefectSG.confirm)
