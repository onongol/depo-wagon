from typing import TYPE_CHECKING

from apps.bot.fsm import save_defect

from .register import register_defect

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext

    from apps.bot.user_data import DefectData
    from apps.core.models import Employee

    from .register import PersistResult


async def persist_defect(
    state: FSMContext, defect_data: DefectData, employee: Employee, bot: Bot
) -> PersistResult:
    """Save the defect and record its id in the form; raises as register_defect does."""
    registered = await register_defect(defect_data, employee, bot)
    defect_data.defect_id = str(registered.defect.id)
    await save_defect(state, defect_data)
    return registered
