from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_PHOTO_SKIP
from apps.bot.constants import UD_LAST_PHOTO_MSG
from apps.bot.fsm import load_defect, save_defect, user_lock
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.defects.validators import MAX_PHOTO_BYTES

from .jobs import clear_last_photo_keyboard, schedule_flush
from .routing import after_photos

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message


async def receive_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    """Handle an incoming photo, one album member at a time."""
    photo = message.photo[-1]

    if photo.file_size and photo.file_size > MAX_PHOTO_BYTES:
        await message.answer(str(M.PHOTO_TOO_LARGE))
        return

    user_id = message.from_user.id

    async with user_lock(user_id):
        defect = await load_defect(state)
        defect.photo_file_ids.append(photo.file_id)
        await save_defect(state, defect)
        count = len(defect.photo_file_ids)

        if message.media_group_id:
            # One acknowledgement for the whole album, not one per photo.
            schedule_flush(bot, state, chat_id=message.chat.id, user_id=user_id)
            return

        await clear_last_photo_keyboard(bot, state)
        sent = await message.answer(
            str(M.PHOTO_RECEIVED).format(count=count),
            reply_markup=skip_keyboard(CB_PHOTO_SKIP),
        )
        await state.update_data({UD_LAST_PHOTO_MSG: [sent.chat.id, sent.message_id]})


async def skip_photo(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle photo skip — proceed to next step without photos."""
    await callback.answer()

    defect = await load_defect(state)
    await after_photos(callback.message.edit_text, defect, state)
