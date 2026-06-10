import html
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot import services
from apps.bot.constants import OtpStatus, RegStatus, UD_EMPLOYEE, UD_REG
from apps.bot.user_data import RegData
from apps.bot.messages import BotMessages as M
from apps.bot.states import AUTH_EMAIL, AUTH_OTP

from .utils import show_welcome_menu

logger = logging.getLogger(__name__)


async def receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle OTP code entry, verify, and complete registration if valid."""
    entered = update.message.text.strip()

    reg: RegData | None = context.user_data.get(UD_REG)
    email = reg.email if reg else None

    if not email:
        await update.message.reply_text(str(M.SESSION_ERROR))
        return ConversationHandler.END

    employee_id, status = await services.verify_otp(email, entered)

    if status == OtpStatus.EXPIRED:
        context.user_data.pop(UD_REG, None)
        await update.message.reply_text(str(M.OTP_EXPIRED))
        return AUTH_EMAIL

    if status == OtpStatus.MAX_ATTEMPTS:
        context.user_data.pop(UD_REG, None)
        await update.message.reply_text(str(M.OTP_MAX_ATTEMPTS))
        return AUTH_EMAIL

    if status == OtpStatus.WRONG:
        await update.message.reply_text(str(M.OTP_WRONG))
        return AUTH_OTP

    telegram_id = update.effective_user.id

    try:
        employee = await services.get_employee_by_id(employee_id)
        password, reg_status = await services.register_employee(employee, telegram_id)
    except Exception:
        logger.exception("Registration failed for employee_id=%s", employee_id)
        await update.message.reply_text(str(M.SESSION_ERROR))
        return ConversationHandler.END

    if reg_status == RegStatus.CREATED:
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

    employee.telegram_id = telegram_id
    context.user_data[UD_EMPLOYEE] = employee
    await show_welcome_menu(update.message, employee)

    context.user_data.pop(UD_REG, None)
    return ConversationHandler.END
