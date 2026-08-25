import html
import logging
import re

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot import services
from apps.bot.constants import UD_REG
from apps.bot.user_data import RegData
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

    employee, status = await services.get_employee_for_auth(
        email, update.effective_user.id
    )

    if status == "not_found":
        await update.message.reply_text(
            str(M.EMAIL_NOT_FOUND).format(email=html.escape(email)),
            parse_mode=M.PARSE_MODE,
        )
        return AUTH_EMAIL

    if status == "already_linked":
        await update.message.reply_text(str(M.EMAIL_ALREADY_LINKED))
        return ConversationHandler.END

    try:
        otp_code = await services.generate_and_store_otp(email, employee.id)
        sent = await services.send_otp_email(email, otp_code, employee.first_name)
    except Exception:
        logger.exception("OTP generation/send failed for %s", email)
        await update.message.reply_text(str(M.OTP_SEND_FAILED))
        return AUTH_EMAIL

    context.user_data[UD_REG] = RegData(email=email)

    if sent:
        await update.message.reply_text(
            str(M.OTP_SENT).format(email=html.escape(email)),
            parse_mode=M.PARSE_MODE,
        )
    else:
        await update.message.reply_text(str(M.OTP_SEND_FAILED))
        return AUTH_EMAIL

    return AUTH_OTP
