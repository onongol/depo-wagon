import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.callbacks import PhotoSkipCB
from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import measurement_choice_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import MEASUREMENT_CHOICE, PHOTO
from apps.bot.user_data import DefectData
from apps.defects.validators import MAX_PHOTO_BYTES

logger = logging.getLogger(__name__)

PHOTO_MG = "photo_mg_"


async def _flush_media_group(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send batched photo count after all album photos are collected."""
    user_id = context.job.user_id
    chat_id = context.job.chat_id
    defect: DefectData | None = context.application.user_data.get(user_id, {}).get(
        UD_DEFECT
    )
    count = len(defect.photo_file_ids) if defect else 0

    await context.bot.send_message(
        chat_id=chat_id,
        text=str(M.PHOTO_RECEIVED).format(count=count),
        reply_markup=skip_keyboard(PhotoSkipCB()),
    )


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle incoming photo or skip action."""
    if update.callback_query:
        # User pressed Skip → move to measurement step
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            str(M.ASK_MEASUREMENT),
            reply_markup=measurement_choice_keyboard(),
        )
        return MEASUREMENT_CHOICE

    # Collect photo (highest resolution)
    photo = update.message.photo[-1]

    # Validate photo size before downloading
    if photo.file_size and photo.file_size > MAX_PHOTO_BYTES:
        await update.message.reply_text(str(M.PHOTO_TOO_LARGE))
        return PHOTO

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.photo_file_ids.append(photo.file_id)

    if update.message.media_group_id and context.job_queue is not None:
        # Album: reset debounce timer on each new photo
        job_name = f"{PHOTO_MG}{update.effective_user.id}"
        for job in context.job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()
        context.job_queue.run_once(
            _flush_media_group,
            when=0.5,
            name=job_name,
            user_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
        )
    else:
        # Single photo: respond immediately
        await update.message.reply_text(
            str(M.PHOTO_RECEIVED).format(count=len(defect.photo_file_ids)),
            reply_markup=skip_keyboard(PhotoSkipCB()),
        )

    return PHOTO
