from telegram import Update
from telegram.ext import ContextTypes

from apps.bot import services

from apps.bot.constants import UD_EMPLOYEE


async def get_employee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get employee from context cache or DB."""
    employee = context.user_data.get(UD_EMPLOYEE)
    
    if not employee:
        telegram_id = update.effective_user.id
        employee = await services.get_employee_by_telegram_id(telegram_id)
        if employee:
            context.user_data[UD_EMPLOYEE] = employee
    return employee
