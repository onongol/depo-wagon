import logging

from telegram.ext import ConversationHandler

from apps.bot import services
from apps.bot.constants import UD_LAST_PHOTO_MSG, UD_RESP_EMPLOYEES, UD_RESP_SEARCH
from apps.bot.keyboards.defect import measurement_choice_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import MEASUREMENT_CHOICE, RESPONSIBLE_EMPLOYEE
from apps.bot.user_data import DefectData
from apps.defects.constants import DefectType

logger = logging.getLogger(__name__)


async def after_photos(query_or_msg, defect: DefectData, context, edit: bool) -> int:
    """Route to responsible_employee or measurement depending on defect type."""
    context.user_data.pop(UD_LAST_PHOTO_MSG, None)

    if defect.defect_type == DefectType.HUMAN_FACTOR:
        from apps.bot.handlers.defect.responsible_employee import (
            show_responsible_employee_list,
        )

        try:
            employees = await services.get_employees_by_department(
                defect.department or ""
            )
        except Exception:
            logger.exception("Failed to fetch employees in after_photos")
            await query_or_msg.reply_text(str(M.SESSION_ERROR))
            return ConversationHandler.END

        context.user_data[UD_RESP_EMPLOYEES] = employees
        context.user_data[UD_RESP_SEARCH] = ""
        await show_responsible_employee_list(query_or_msg, context, page=0, edit=edit)
        return RESPONSIBLE_EMPLOYEE

    text = str(M.ASK_MEASUREMENT)
    if edit:
        await query_or_msg.edit_message_text(
            text, reply_markup=measurement_choice_keyboard()
        )
    else:
        await query_or_msg.reply_text(text, reply_markup=measurement_choice_keyboard())
    return MEASUREMENT_CHOICE
