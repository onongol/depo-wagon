from typing import TYPE_CHECKING

from apps.bot.callbacks import PhotoSkipCB
from apps.bot.constants import PHOTO_MG_JOB_PREFIX, UD_DEFECT, UD_LAST_PHOTO_MSG
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import PHOTO
from apps.defects.validators import MAX_PHOTO_BYTES

from .jobs import clear_last_photo_keyboard, flush_media_group
from .routing import after_photos

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes

    from apps.bot.user_data import DefectData


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle incoming photo."""
    photo = update.message.photo[-1]

    if photo.file_size and photo.file_size > MAX_PHOTO_BYTES:
        await update.message.reply_text(str(M.PHOTO_TOO_LARGE))
        return PHOTO

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.photo_file_ids.append(photo.file_id)

    if update.message.media_group_id and context.job_queue is not None:
        job_name = f"{PHOTO_MG_JOB_PREFIX}{update.effective_user.id}"
        for job in context.job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()
        context.job_queue.run_once(
            flush_media_group,
            when=0.5,
            name=job_name,
            user_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
        )
    else:
        await clear_last_photo_keyboard(context.bot, context.user_data)
        msg = await update.message.reply_text(
            str(M.PHOTO_RECEIVED).format(count=len(defect.photo_file_ids)),
            reply_markup=skip_keyboard(PhotoSkipCB()),
        )
        context.user_data[UD_LAST_PHOTO_MSG] = [msg.chat_id, msg.message_id]

    return PHOTO


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo skip — proceed to next step without photos."""
    query = update.callback_query
    await query.answer()

    defect: DefectData = context.user_data[UD_DEFECT]
    return await after_photos(query, defect, context, edit=True)
