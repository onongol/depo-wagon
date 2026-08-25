import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot import services
from apps.bot.constants import UD_EMPLOYEE
from apps.bot.messages import BotMessages as M
from apps.bot.states import AUTH_EMAIL

from .utils import show_welcome_menu

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point. If already registered → show menu.
    Otherwise → ask for email to begin registration.
    """
    telegram_id = update.effective_user.id

    try:
        employee = await services.get_employee_by_telegram_id(telegram_id)
    except Exception:
        logger.exception("DB lookup failed for telegram_id=%s", telegram_id)
        await update.message.reply_text(str(M.SESSION_ERROR))
        return ConversationHandler.END

    if employee:
        context.user_data[UD_EMPLOYEE] = employee
        await show_welcome_menu(update.message, employee)
        return ConversationHandler.END

    context.user_data.clear()

    await update.message.reply_text(
        str(M.WELCOME_NEW),
        parse_mode=M.PARSE_MODE,
    )
    return AUTH_EMAIL
