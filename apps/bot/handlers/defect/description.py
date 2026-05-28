import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.keyboards import confirm_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import CONFIRM, DESC

from .summary import build_summary

logger = logging.getLogger(__name__)


async def receive_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle incoming description text or skip action."""
    if update.callback_query:
        await update.callback_query.answer()
        context.user_data["defect"]["description"] = ""
        await update.callback_query.edit_message_text(
            build_summary(context.user_data["defect"]),
            parse_mode=M.PARSE_MODE,
            reply_markup=confirm_keyboard(),
        )
    else:
        text = update.message.text.strip()
        if len(text) > 1000:
            await update.message.reply_text(
                str(M.DESCRIPTION_TOO_LONG).format(length=len(text), max=1000),
                parse_mode=M.PARSE_MODE,
            )
            return DESC
        context.user_data["defect"]["description"] = text
        await update.message.reply_text(
            build_summary(context.user_data["defect"]),
            parse_mode=M.PARSE_MODE,
            reply_markup=confirm_keyboard(),
        )
    return CONFIRM
