import html
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot import services
from apps.bot.keyboards import main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import AUTH_EMAIL, AUTH_OTP

logger = logging.getLogger(__name__)


async def receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle OTP code entry, verify, and complete registration if valid."""
    entered = update.message.text.strip()
    reg = context.user_data.get("reg", {})
    email = reg.get("email")

    if not email:
        await update.message.reply_text(str(M.SESSION_ERROR))
        return ConversationHandler.END

    employee_id, status = services.verify_otp(email, entered)

    if status == "expired":
        context.user_data.pop("reg", None)
        await update.message.reply_text(str(M.OTP_EXPIRED))
        return AUTH_EMAIL

    if status == "max_attempts":
        context.user_data.pop("reg", None)
        await update.message.reply_text(str(M.OTP_MAX_ATTEMPTS))
        return AUTH_EMAIL

    if status == "wrong":
        await update.message.reply_text(str(M.OTP_WRONG))
        return AUTH_OTP

    # OTP verified — fetch employee and register
    employee = await services.get_employee_by_id(employee_id)
    telegram_id = update.effective_user.id
    password, reg_status = await services.register_employee(employee, telegram_id)

    if reg_status == "created":
        await services.send_credentials_email(email, password, employee.first_name)
        await update.message.reply_text(
            str(M.REGISTERED_NEW).format(email=html.escape(email)),
            parse_mode=M.PARSE_MODE,
        )
    else:
        await update.message.reply_text(
            str(M.TELEGRAM_LINKED),
            parse_mode=M.PARSE_MODE,
        )

    # Refresh employee from DB to get updated fields
    employee = await services.get_employee_by_telegram_id(telegram_id)
    context.user_data["employee"] = employee

    await update.message.reply_text(
        str(M.WELCOME_MENU).format(
            full_name=employee.full_name,
            role=employee.get_role_display(),
        ),
        parse_mode=M.PARSE_MODE,
        reply_markup=main_menu_keyboard(employee.role),
    )

    context.user_data.pop("reg", None)
    return ConversationHandler.END
