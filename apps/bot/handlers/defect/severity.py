import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.constants import SEVERITY_LABELS
from apps.bot.keyboards import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import PHOTO

logger = logging.getLogger(__name__)


async def receive_severity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    sev_value = query.data.split(":", 1)[1]
    sev_label = SEVERITY_LABELS.get(sev_value, sev_value)
    context.user_data["defect"]["severity"] = sev_value
    context.user_data["defect"]["severity_label"] = sev_label

    await query.edit_message_text(
        str(M.SEVERITY_CONFIRMED).format(label=sev_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard("photo:skip"),
    )
    return PHOTO
