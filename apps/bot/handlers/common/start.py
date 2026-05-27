import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot import services
from apps.bot.keyboards import main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import AUTH_EMAIL

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point. If already registered → show menu.
    Otherwise → ask for email to begin registration.
    """
    telegram_id = update.effective_user.id
    employee = await services.get_employee_by_telegram_id(telegram_id)

    if employee:
        context.user_data["employee"] = employee
        await update.message.reply_text(
            str(M.WELCOME_MENU).format(
                full_name=employee.full_name,
                role=employee.get_role_display(),
            ),
            parse_mode=M.PARSE_MODE,
            reply_markup=main_menu_keyboard(employee.role),
        )
        return ConversationHandler.END

    context.user_data.pop("reg", None)
    await update.message.reply_text(
        str(M.WELCOME_NEW),
        parse_mode=M.PARSE_MODE,
    )
    return AUTH_EMAIL
