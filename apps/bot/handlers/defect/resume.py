"""Each step's screen, redrawn from the form so Continue can show it again."""

from typing import TYPE_CHECKING

from apps.bot.fsm import load_defect

from .scene import as_send_kwargs
from .scenes import scene_for

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.fsm.context import FSMContext


async def show_current_step(send: Callable[..., Awaitable], state: FSMContext) -> bool:
    """False for saving, the one step with no screen of its own."""
    scene = scene_for(await state.get_state())
    if scene is None:
        return False

    content, keyboard = await scene.draw(
        await load_defect(state), await state.get_data()
    )
    await send(**as_send_kwargs(content), reply_markup=keyboard)
    return True
