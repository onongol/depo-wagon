from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.callbacks import PartNumberSkipCB
from apps.bot.constants import UD_DEFECT, UD_EDITING
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import PART_NUMBER
from apps.bot.user_data import DefectData
from apps.defects.constants import DefectNode

from .summary import show_summary

_NODE_LABELS = dict(DefectNode.choices)


async def receive_node(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle incoming node selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    node_value = query.data.value
    node_label = _NODE_LABELS.get(node_value, node_value)

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.node = node_value
    defect.node_label = node_label

    if context.user_data.get(UD_EDITING):
        return await show_summary(update, context, defect)

    await query.edit_message_text(
        str(M.NODE_CONFIRMED).format(label=node_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(PartNumberSkipCB()),
    )
    return PART_NUMBER
