"""User-facing side of support: the /support dialog that relays a question."""

import html
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.handlers.employee import get_employee
from apps.bot.messages import BotMessages as M
from apps.bot.states import SUPPORT_MESSAGE

from .utils import remember_request, support_chat_id

logger = logging.getLogger(__name__)


async def support_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry: /support — ask the user to type their question."""
    if support_chat_id() is None:
        await update.message.reply_text(
            str(M.SUPPORT_UNAVAILABLE), parse_mode=M.PARSE_MODE
        )
        return ConversationHandler.END

    await update.message.reply_text(str(M.SUPPORT_ASK), parse_mode=M.PARSE_MODE)
    return SUPPORT_MESSAGE


async def support_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Relay the user's question to the support chat with their identity."""
    chat_id = support_chat_id()
    if chat_id is None:
        await update.message.reply_text(
            str(M.SUPPORT_UNAVAILABLE), parse_mode=M.PARSE_MODE
        )
        return ConversationHandler.END

    question = update.message.text.strip()
    user = update.effective_user

    try:
        employee = await get_employee(update, context)
    except Exception:
        logger.exception("Failed to resolve employee for support request")
        employee = None

    if employee:
        identity = (
            f"{employee.full_name} "
            f"({employee.employee_id}, {employee.get_role_display()})"
        )
    else:
        identity = user.full_name or user.first_name

    text = str(M.SUPPORT_REQUEST).format(
        identity=html.escape(identity),
        username=f"@{user.username}" if user.username else "—",
        question=html.escape(question),
    )

    try:
        sent = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=M.PARSE_MODE,
        )
    except Exception:
        logger.exception("Failed to relay support request from %s", user.id)
        await update.message.reply_text(
            str(M.SUPPORT_UNAVAILABLE), parse_mode=M.PARSE_MODE
        )
        return ConversationHandler.END

    await remember_request(sent.message_id, user.id)

    await update.message.reply_text(str(M.SUPPORT_SENT))
    return ConversationHandler.END
