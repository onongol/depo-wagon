from typing import TYPE_CHECKING

from apps.bot import services

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


async def get_employee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return the active employee this chat belongs to, or None.

    Read on every update rather than cached: disconnecting or deactivating
    someone on the web has to reach the bot at once, and a copy held in
    user_data would outlive that until the process restarts.
    """
    return await services.get_employee_by_telegram_id(update.effective_user.id)
