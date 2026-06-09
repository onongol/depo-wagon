import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.defect import node_keyboard_for_department
from apps.bot.messages import BotMessages as M
from apps.bot.states import NODE
from apps.bot.user_data import DefectData

logger = logging.getLogger(__name__)


async def receive_department(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle department selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    dept_value = query.data.value

    from apps.core.constants import Department

    dept_label = dict(Department.choices).get(dept_value, dept_value)

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.department = dept_value
    defect.department_label = dept_label

    await query.edit_message_text(
        str(M.DEPARTMENT_CONFIRMED).format(label=dept_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=node_keyboard_for_department(dept_value),
    )
    return NODE
