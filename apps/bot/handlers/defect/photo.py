import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.keyboards import measurement_choice_keyboard, skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import MEASUREMENT_CHOICE, PHOTO

logger = logging.getLogger(__name__)


async def _flush_media_group(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send batched photo count after all album photos are collected."""
    user_id = context.job.user_id
    chat_id = context.job.chat_id
    defect = context.application.user_data.get(user_id, {}).get("defect", {})
    count = len(defect.get("photo_file_ids", []))

    await context.bot.send_message(
        chat_id=chat_id,
        text=str(M.PHOTO_RECEIVED).format(count=count),
        reply_markup=skip_keyboard("photo:skip"),
    )


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle incoming photo or skip action."""
    if update.callback_query:
        # User pressed Skip → move to measurement step
        await update.callback_query.answer()
        context.user_data["defect"].setdefault("measurements", [])
        await update.callback_query.edit_message_text(
            str(M.ASK_MEASUREMENT),
            reply_markup=measurement_choice_keyboard(),
        )
        return MEASUREMENT_CHOICE

    # Collect photo (highest resolution)
    photo = update.message.photo[-1]
    photo_ids = context.user_data["defect"].setdefault("photo_file_ids", [])
    photo_ids.append(photo.file_id)

    if update.message.media_group_id:
        # Album: reset debounce timer on each new photo
        job_name = f"photo_mg_{update.effective_user.id}"
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
            str(M.PHOTO_RECEIVED).format(count=len(photo_ids)),
            reply_markup=skip_keyboard("photo:skip"),
        )

    return PHOTO
