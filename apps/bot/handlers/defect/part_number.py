from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.constants import UD_DEFECT, UD_EDITING
from apps.bot.keyboards.defect import defect_type_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DEFECT_TYPE
from apps.bot.user_data import DefectData

from .summary import show_summary


def _get_defect(context: ContextTypes.DEFAULT_TYPE) -> DefectData | None:
    return context.user_data.get(UD_DEFECT)


async def receive_part_number(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle part number text input."""
    defect = _get_defect(context)
    if defect is None:
        await update.message.reply_text(str(M.DEFECT_CANCELLED))
        return ConversationHandler.END

    defect.part_number = update.message.text.strip()

    if context.user_data.get(UD_EDITING):
        return await show_summary(update, context, defect)

    await update.message.reply_text(
        str(M.PART_NUMBER_CONFIRMED).format(part_number=defect.part_number),
        parse_mode=M.PARSE_MODE,
        reply_markup=defect_type_keyboard(),
    )
    return DEFECT_TYPE


async def skip_part_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle part number skip."""
    query = update.callback_query
    await query.answer()

    defect = _get_defect(context)
    if defect is None:
        await query.edit_message_text(str(M.DEFECT_CANCELLED))
        return ConversationHandler.END

    defect.part_number = ""

    if context.user_data.get(UD_EDITING):
        return await show_summary(update, context, defect)

    await query.edit_message_text(
        str(M.PART_NUMBER_SKIPPED),
        parse_mode=M.PARSE_MODE,
        reply_markup=defect_type_keyboard(),
    )
    return DEFECT_TYPE
