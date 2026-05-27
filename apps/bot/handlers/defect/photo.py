import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.keyboards import measurement_choice_keyboard, skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import MEASUREMENT_CHOICE, PHOTO

logger = logging.getLogger(__name__)


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        # User pressed Skip → move to measurement step
        await update.callback_query.answer()
        context.user_data["defect"].setdefault("measurements", [])
        await update.callback_query.edit_message_text(
            str(M.ASK_MEASUREMENT),
            reply_markup=measurement_choice_keyboard(),
        )
        return MEASUREMENT_CHOICE

    # User sent a photo — add to list, stay in PHOTO state
    photo = update.message.photo[-1]  # highest resolution
    photo_ids = context.user_data["defect"].setdefault("photo_file_ids", [])
    photo_ids.append(photo.file_id)
    count = len(photo_ids)

    await update.message.reply_text(
        str(M.PHOTO_RECEIVED).format(count=count),
        reply_markup=skip_keyboard("photo:skip"),
    )
    return PHOTO
