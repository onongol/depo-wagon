from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.defect import confirm_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import CONFIRM, DESC
from apps.bot.user_data import DefectData

from .summary import build_summary


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
    await update.message.reply_text(
        build_summary(defect),
        parse_mode=M.PARSE_MODE,
        reply_markup=confirm_keyboard(),
    )
    return CONFIRM


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle description skip — set empty description and show summary."""
    query = update.callback_query
    await query.answer()

    defect = _get_defect(context)
    if defect is None:
        await query.edit_message_text(str(M.DEFECT_CANCELLED))
        return ConversationHandler.END

    defect.description = ""
    await query.edit_message_text(
        build_summary(defect),
        parse_mode=M.PARSE_MODE,
        reply_markup=confirm_keyboard(),
    )
    return CONFIRM
