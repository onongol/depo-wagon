import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.keyboards import defect_type_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DEFECT_TYPE

logger = logging.getLogger(__name__)


async def receive_node(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    node_value = query.data.split(":", 1)[1]
    context.user_data["defect"]["node"] = node_value

    from apps.defects.constants import DefectNode

    node_label = dict(DefectNode.choices).get(node_value, node_value)
    context.user_data["defect"]["node_label"] = node_label

    await query.edit_message_text(
        str(M.NODE_CONFIRMED).format(label=node_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=defect_type_keyboard(),
    )
    return DEFECT_TYPE
