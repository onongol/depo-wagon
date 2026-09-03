from typing import TYPE_CHECKING

from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.constants import UD_DEFECT
from apps.bot.messages import BotMessages as M
from apps.bot.states import DESC
from apps.bot.user_data import DefectData

from .summary import show_summary

if TYPE_CHECKING:
    from telegram import Update


def _get_defect(context: ContextTypes.DEFAULT_TYPE) -> DefectData | None:
    return context.user_data.get(UD_DEFECT)


async def receive_description(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle incoming description text."""
    defect = _get_defect(context)
    if defect is None:
        await update.message.reply_text(str(M.DEFECT_CANCELLED))
        return ConversationHandler.END

    text = update.message.text.strip()
    if len(text) > 1000:
        await update.message.reply_text(
            str(M.DESCRIPTION_TOO_LONG).format(length=len(text), max=1000),
            parse_mode=M.PARSE_MODE,
        )
        return DESC

    defect.description = text
    return await show_summary(update, context, defect)


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle description skip — set empty description and show summary."""
    query = update.callback_query
    await query.answer()

    defect = _get_defect(context)
    if defect is None:
        await query.edit_message_text(str(M.DEFECT_CANCELLED))
        return ConversationHandler.END

    defect.description = ""
    return await show_summary(update, context, defect)
