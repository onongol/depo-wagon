from telegram import Update
from telegram.ext import ContextTypes

from apps.bot import services


async def get_employee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get employee from context cache or DB."""
    employee = context.user_data.get("employee")
    if not employee:
        telegram_id = update.effective_user.id
        employee = await services.get_employee_by_telegram_id(telegram_id)
        if employee:
            context.user_data["employee"] = employee
    return employee
