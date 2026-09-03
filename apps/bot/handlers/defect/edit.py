from typing import TYPE_CHECKING

from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.callbacks import DescSkipCB, PartNumberSkipCB
from apps.bot.constants import UD_DEFECT, UD_EDITING
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import (
    defect_type_keyboard,
    node_keyboard_for_department,
    severity_keyboard,
)
from apps.bot.messages import BotMessages as M
from apps.bot.states import (
    CONFIRM,
    DEFECT_TYPE,
    DESC,
    NODE,
    PART_NUMBER,
    SEVERITY,
    WAGON_NUM,
)

if TYPE_CHECKING:
    from telegram import Update

    from apps.bot.user_data import DefectData


async def start_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Render the chosen field's input and route to its state in edit mode."""
    query = update.callback_query
    await query.answer()

    defect: DefectData | None = context.user_data.get(UD_DEFECT)
    if defect is None:
        await query.edit_message_text(str(M.DEFECT_CANCELLED))
        return ConversationHandler.END

    field = query.data.field
    context.user_data[UD_EDITING] = True

    if field == "wagon":
        await query.edit_message_text(str(M.EDIT_WAGON), parse_mode=M.PARSE_MODE)
        return WAGON_NUM

    if field == "node":
        await query.edit_message_text(
            str(M.EDIT_NODE),
            parse_mode=M.PARSE_MODE,
            reply_markup=node_keyboard_for_department(defect.department or ""),
        )
        return NODE

    if field == "part_number":
        await query.edit_message_text(
            str(M.EDIT_PART_NUMBER),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard(PartNumberSkipCB()),
        )
        return PART_NUMBER

    if field == "defect_type":
        await query.edit_message_text(
            str(M.EDIT_DEFECT_TYPE),
            parse_mode=M.PARSE_MODE,
            reply_markup=defect_type_keyboard(),
        )
        return DEFECT_TYPE

    if field == "severity":
        await query.edit_message_text(
            str(M.EDIT_SEVERITY),
            parse_mode=M.PARSE_MODE,
            reply_markup=severity_keyboard(),
        )
        return SEVERITY

    if field == "description":
        await query.edit_message_text(
            str(M.EDIT_DESCRIPTION),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard(DescSkipCB()),
        )
        return DESC

    # Unknown field — fall back to the summary state unchanged.
    context.user_data.pop(UD_EDITING, None)
    return CONFIRM
