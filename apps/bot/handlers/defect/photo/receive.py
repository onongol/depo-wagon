import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError

from apps.bot.callback_data import CB_PHOTO_SKIP
from apps.bot.constants import UD_LAST_MEDIA_GROUP, UD_LAST_PHOTO_MSG
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import done_keyboard
from apps.bot.messages import BotMessages as M
from apps.defects.validators import MAX_PHOTO_BYTES

from .routing import after_photos

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)


async def clear_last_photo_keyboard(bot: Bot, state: FSMContext) -> None:
    """Remove the inline keyboard from the previous photo acknowledgement."""
    data = await state.get_data()
    ref = data.pop(UD_LAST_PHOTO_MSG, None)
    if not ref:
        return

    await state.set_data(data)
    chat_id, message_id = ref
    try:
        await bot.edit_message_reply_markup(
            chat_id=chat_id, message_id=message_id, reply_markup=None
        )
    except TelegramAPIError:
        logger.debug("Could not clear photo keyboard (message deleted or too old)")


async def receive_photo(message: Message, state: FSMContext, bot: Bot) -> None:
    """Record a photo, answering a lone one and only the first of an album.

    Telegram sends an album as separate updates with no end marker, so the rest
    of it is recorded silently and the total is shown on Done.
    """
    photo = message.photo[-1]

    if photo.file_size and photo.file_size > MAX_PHOTO_BYTES:
        await message.answer(str(M.PHOTO_TOO_LARGE))
        return

    defect = await load_defect(state)
    defect.photo_file_ids.append(photo.file_id)
    await save_defect(state, defect)

    group = message.media_group_id
    if group and (await state.get_data()).get(UD_LAST_MEDIA_GROUP) == group:
        return

    if group:
        text = str(M.PHOTO_ALBUM_RECEIVING)
    else:
        text = str(M.PHOTO_RECEIVED).format(count=len(defect.photo_file_ids))

    await clear_last_photo_keyboard(bot, state)
    sent = await message.answer(text, reply_markup=done_keyboard(CB_PHOTO_SKIP))
    await state.update_data(
        {
            UD_LAST_PHOTO_MSG: [sent.chat.id, sent.message_id],
            UD_LAST_MEDIA_GROUP: group,
        }
    )


async def skip_photo(callback: CallbackQuery, state: FSMContext) -> None:
    """Leave the photo step, reporting how many photos were attached."""
    defect = await load_defect(state)
    count = len(defect.photo_file_ids) if defect else 0

    await callback.answer(str(M.PHOTOS_ATTACHED).format(count=count) if count else None)
    await after_photos(callback.message.edit_text, defect, state)
