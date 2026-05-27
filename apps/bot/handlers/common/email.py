import html
import logging
import re

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot import services
from apps.bot.messages import BotMessages as M
from apps.bot.states import AUTH_EMAIL, AUTH_OTP

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle email entry, find employee, and send OTP."""
    email = update.message.text.strip()

    if not EMAIL_REGEX.match(email):
        await update.message.reply_text(
            str(M.EMAIL_INVALID),
            parse_mode=M.PARSE_MODE,
        )
        return AUTH_EMAIL

    employee = await services.get_employee_by_email(email)

    if not employee:
        await update.message.reply_text(
            str(M.EMAIL_NOT_FOUND).format(email=html.escape(email)),
            parse_mode=M.PARSE_MODE,
        )
        return AUTH_EMAIL

    # Check if already linked to another Telegram account
    telegram_id = update.effective_user.id
    if employee.telegram_id and employee.telegram_id != telegram_id:
        await update.message.reply_text(str(M.EMAIL_ALREADY_LINKED))
        return ConversationHandler.END

    # Generate OTP and send to email
    otp_code = services.generate_and_store_otp(email, employee.id)
    sent = await services.send_otp_email(email, otp_code, employee.first_name)

    context.user_data["reg"] = {"email": email}

    if sent:
        await update.message.reply_text(
            str(M.OTP_SENT).format(email=html.escape(email)),
            parse_mode=M.PARSE_MODE,
        )
    else:
        await update.message.reply_text(str(M.OTP_SEND_FAILED))
        return AUTH_EMAIL

    return AUTH_OTP
