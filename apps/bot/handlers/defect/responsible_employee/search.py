from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.constants import UD_RESP_SEARCH
from apps.bot.states import RESPONSIBLE_EMPLOYEE

from .list import show_responsible_employee_list


async def search_responsible_employee(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle text input as a search query for responsible employee."""
    context.user_data[UD_RESP_SEARCH] = update.message.text.strip()
    await show_responsible_employee_list(update.message, context, page=0, edit=False)
    return RESPONSIBLE_EMPLOYEE
