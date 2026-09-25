import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError

from apps.bot import services
from apps.bot.constants import UD_DEFECT, VERDICT_LABELS
from apps.bot.fsm import load_defect
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.defects.constants import DefectVerdict

from .notifications import notify_decommission

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import VerdictCB
    from apps.core.models import Employee

logger = logging.getLogger(__name__)


async def receive_employee_verdict(
    callback: CallbackQuery,
    callback_data: VerdictCB,
    state: FSMContext,
    bot: Bot,
    employee: Employee | None,
) -> None:
    """Handle incoming verdict selection from inline keyboard."""
    await callback.answer()

    verdict_value = callback_data.value

    defect = await load_defect(state)
    if not employee:
        await callback.message.edit_text(str(M.NOT_REGISTERED))
        await state.set_state(None)
        return

    if defect.defect_id:
        try:
            await services.save_employee_verdict(defect.defect_id, verdict_value)
        except Exception:
            logger.exception("Failed to save verdict for defect %s", defect.defect_id)
            await callback.message.edit_text(str(M.SESSION_ERROR))
            await state.set_state(None)
            return

        if verdict_value == DefectVerdict.DECOMMISSION:
            await notify_decommission(bot, employee, defect)

    verdict_label = str(VERDICT_LABELS.get(verdict_value, verdict_value))

    # Prevent re-clicking verdict buttons after the flow ends
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramAPIError:
        logger.debug("Could not clear verdict keyboard (message deleted or too old)")

    await callback.message.answer(
        str(M.VERDICT_DONE).format(label=verdict_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=main_menu_keyboard(),
    )

    data = await state.get_data()
    data.pop(UD_DEFECT, None)
    await state.set_data(data)
    await state.set_state(None)
