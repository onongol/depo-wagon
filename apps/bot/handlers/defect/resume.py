"""Each plain step's screen, rebuilt from the form so Continue can show it again.

A step that is a Scene draws its own; the table shrinks as steps move.
"""

from typing import TYPE_CHECKING

from apps.bot.fsm import load_defect
from apps.bot.keyboards.confirm import employee_verdict_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

from .scene import as_send_kwargs
from .scenes import scene_for

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext


# As each step first showed it
_SCREENS = {
    DefectSG.employee_verdict.state: lambda _: (
        str(M.ASK_EMPLOYEE_VERDICT),
        employee_verdict_keyboard(),
    ),
}


async def show_current_step(send: Callable[..., Awaitable], state: FSMContext) -> bool:
    """False for saving, the one step with no screen of its own."""
    step = await state.get_state()
    defect = await load_defect(state)

    if scene := scene_for(step):
        content, keyboard = await scene.draw(defect, await state.get_data())
        await send(**as_send_kwargs(content), reply_markup=keyboard)
    elif screen := _SCREENS.get(step):
        content, keyboard = screen(defect)
        await send(**as_send_kwargs(content), reply_markup=keyboard)
    else:
        return False

    return True
