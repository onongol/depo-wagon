from typing import TYPE_CHECKING

from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.callback_data import CB_DESC_SKIP, CB_PART_NUMBER_SKIP
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


# field -> (prompt, keyboard built from the defect under edit, state to enter).
# Keyboards are built per call: their callback payloads are per-message.
_EDIT_STEPS = {
    "wagon": (M.EDIT_WAGON, None, WAGON_NUM),
    "node": (
        M.EDIT_NODE,
        lambda defect: node_keyboard_for_department(defect.department or ""),
        NODE,
    ),
    "part_number": (
        M.EDIT_PART_NUMBER,
        lambda _: skip_keyboard(CB_PART_NUMBER_SKIP),
        PART_NUMBER,
    ),
    "defect_type": (M.EDIT_DEFECT_TYPE, lambda _: defect_type_keyboard(), DEFECT_TYPE),
    "severity": (M.EDIT_SEVERITY, lambda _: severity_keyboard(), SEVERITY),
    "description": (M.EDIT_DESCRIPTION, lambda _: skip_keyboard(CB_DESC_SKIP), DESC),
}


async def start_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Render the chosen field's input and route to its state in edit mode."""
    query = update.callback_query
    await query.answer()

    defect: DefectData | None = context.user_data.get(UD_DEFECT)
    if defect is None:
        await query.edit_message_text(str(M.DEFECT_CANCELLED))
        return ConversationHandler.END

    context.user_data[UD_EDITING] = True

    step = _EDIT_STEPS.get(query.data.field)
    if step is None:
        context.user_data.pop(UD_EDITING, None)
        return CONFIRM

    prompt, keyboard, state = step
    await query.edit_message_text(
        str(prompt),
        parse_mode=M.PARSE_MODE,
        reply_markup=keyboard(defect) if keyboard else None,
    )
    return state
