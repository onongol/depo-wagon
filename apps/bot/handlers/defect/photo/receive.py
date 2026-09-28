import logging
from bisect import insort
from operator import attrgetter
from typing import TYPE_CHECKING, Any

from aiogram import F
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.scene import on

from apps.bot.callback_data import CB_PHOTO_SKIP
from apps.bot.constants import UD_LAST_MEDIA_GROUP, UD_LAST_PHOTO_MSG
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.defect.scene import DefectScene
from apps.bot.handlers.defect.text import (
    build_album_receiving_text,
    build_photo_received_text,
    build_photo_too_large_text,
    build_photos_attached_toast,
    build_severity_confirmed_text,
)
from apps.bot.keyboards.common import done_keyboard, skip_keyboard
from apps.bot.states import DefectSG
from apps.bot.user_data import PhotoEntry
from apps.defects.validators import MAX_PHOTO_BYTES

from .routing import after_photos

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

    from apps.bot.handlers.defect.scene import Screen
    from apps.bot.user_data import DefectData

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


class PhotoScene(DefectScene, state=DefectSG.photo.state):
    """Photos until Done; an album is answered once, as its photos queue behind the lock."""

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if form.photos:
            text = build_photo_received_text(len(form.photos))
            return text, done_keyboard(CB_PHOTO_SKIP)
        text = build_severity_confirmed_text(form.severity_label)
        return text, skip_keyboard(CB_PHOTO_SKIP)

    @on.message(F.photo)
    async def receive(self, message: Message, state: FSMContext, bot: Bot) -> None:
        photo = message.photo[-1]

        if photo.file_size and photo.file_size > MAX_PHOTO_BYTES:
            await message.answer(**build_photo_too_large_text().as_kwargs())
            return

        defect = await load_defect(state)
        insort(
            defect.photos,
            PhotoEntry(file_id=photo.file_id, message_id=message.message_id),
            key=attrgetter("message_id"),
        )
        await save_defect(state, defect)

        group = message.media_group_id
        if group and (await state.get_data()).get(UD_LAST_MEDIA_GROUP) == group:
            return

        if group:
            text = build_album_receiving_text()
        else:
            text = build_photo_received_text(len(defect.photos))

        await clear_last_photo_keyboard(bot, state)

        sent = await message.answer(
            **text.as_kwargs(), reply_markup=done_keyboard(CB_PHOTO_SKIP)
        )
        await state.update_data(
            {
                UD_LAST_PHOTO_MSG: [sent.chat.id, sent.message_id],
                UD_LAST_MEDIA_GROUP: group,
            }
        )

    @on.callback_query(F.data == CB_PHOTO_SKIP)
    async def skip(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Done and Skip alike, reporting how many photos were attached."""
        defect = await load_defect(state)
        count = len(defect.photos)

        await callback.answer(build_photos_attached_toast(count) if count else None)
        await after_photos(self.wizard, defect, state)
