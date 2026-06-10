import logging

from telegram.ext import ContextTypes

from apps.bot.callbacks import PhotoSkipCB
from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.user_data import DefectData

logger = logging.getLogger(__name__)

PHOTO_MG = "photo_mg_"
UD_LAST_PHOTO_MSG = "_last_photo_msg"


async def clear_last_photo_keyboard(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the inline keyboard from the previous photo-count message."""
    prev_msg = context.user_data.pop(UD_LAST_PHOTO_MSG, None)
    if prev_msg:
        try:
            await prev_msg.edit_reply_markup(reply_markup=None)
        except Exception:
            logger.debug("Could not clear photo keyboard (message deleted or too old)")


async def flush_media_group(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send batched photo count after all album photos are collected."""
    user_id = context.job.user_id
    chat_id = context.job.chat_id
    user_data = context.application.user_data.get(user_id, {})
    defect: DefectData | None = user_data.get(UD_DEFECT)
    count = len(defect.photo_file_ids) if defect else 0

    await clear_last_photo_keyboard(context)
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=str(M.PHOTO_RECEIVED).format(count=count),
        reply_markup=skip_keyboard(PhotoSkipCB()),
    )
    user_data[UD_LAST_PHOTO_MSG] = msg
