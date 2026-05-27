import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.keyboards import confirm_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import CONFIRM

from .summary import build_summary

logger = logging.getLogger(__name__)


async def receive_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        context.user_data["defect"]["description"] = ""
        await update.callback_query.edit_message_text(
            build_summary(context.user_data["defect"]),
            parse_mode=M.PARSE_MODE,
            reply_markup=confirm_keyboard(),
        )
    else:
        context.user_data["defect"]["description"] = update.message.text.strip()
        await update.message.reply_text(
            build_summary(context.user_data["defect"]),
            parse_mode=M.PARSE_MODE,
            reply_markup=confirm_keyboard(),
        )
    return CONFIRM
