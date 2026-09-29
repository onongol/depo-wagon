from bisect import insort
from operator import attrgetter
from typing import TYPE_CHECKING, Any

from aiogram import F
from aiogram.fsm.scene import on

from apps.bot.callback_data import CB_PHOTO_CLEAR, CB_PHOTO_SKIP
from apps.bot.constants import UD_EDITING, UD_LAST_MEDIA_GROUP
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.defect.scene import DefectScene
from apps.bot.handlers.defect.text import (
    build_album_receiving_text,
    build_defect_type_confirmed_text,
    build_edit_photos_text,
    build_photo_received_text,
    build_photo_too_large_text,
    build_photos_attached_toast,
    build_responsible_employee_confirmed_text,
    build_responsible_employee_skipped_text,
)
from apps.bot.keyboards.common import (
    clear_or_done_keyboard,
    done_keyboard,
    skip_keyboard,
)
from apps.bot.states import DefectSG
from apps.bot.user_data import PhotoEntry
from apps.defects.constants import DefectType
from apps.defects.validators import MAX_PHOTO_BYTES

from .routing import after_photos

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery, Message

    from apps.bot.handlers.defect.scene import Screen
    from apps.bot.user_data import DefectData


class PhotoScene(DefectScene, state=DefectSG.photo.state):
    """Photos until Done; an album is answered once, as its photos queue behind the lock."""

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        if form.defect_type == DefectType.HUMAN_FACTOR:
            return DefectSG.responsible_employee
        return DefectSG.defect_type

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        if data.get(UD_EDITING):
            if not form.photos:
                return build_edit_photos_text(0), skip_keyboard(CB_PHOTO_SKIP)
            keyboard = clear_or_done_keyboard(CB_PHOTO_CLEAR, CB_PHOTO_SKIP)
            return build_edit_photos_text(len(form.photos)), keyboard
        if form.photos:
            text = build_photo_received_text(len(form.photos))
            return text, done_keyboard(CB_PHOTO_SKIP)
        if form.defect_type != DefectType.HUMAN_FACTOR:
            text = build_defect_type_confirmed_text(form.defect_type_label)
        elif form.responsible_employee_label:
            text = build_responsible_employee_confirmed_text(
                form.responsible_employee_label
            )
        else:
            text = build_responsible_employee_skipped_text()
        return text, skip_keyboard(CB_PHOTO_SKIP)

    @on.message(F.photo)
    async def receive(self, message: Message, state: FSMContext) -> None:
        """Photos stay in the chat, so the screen goes under them."""
        photo = message.photo[-1]

        if photo.file_size and photo.file_size > MAX_PHOTO_BYTES:
            notice = build_photo_too_large_text()
            await self.show_as_message(message, state, notice=notice, below=True)
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
        await state.update_data({UD_LAST_MEDIA_GROUP: group})

        notice = build_album_receiving_text() if group else None
        await self.show_as_message(message, state, notice=notice, below=True)

    @on.callback_query(F.data == CB_PHOTO_SKIP)
    async def skip(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Done and Skip alike, reporting how many photos were attached."""
        defect = await load_defect(state)
        count = len(defect.photos)

        await callback.answer(build_photos_attached_toast(count) if count else None)
        await after_photos(self, defect, state)

    @on.callback_query(F.data == CB_PHOTO_CLEAR)
    async def clear(self, callback: CallbackQuery, state: FSMContext) -> None:
        """An Edit's way to drop a wrong photo: all of them, then send again."""
        await callback.answer()

        defect = await load_defect(state)
        defect.photos = []
        await save_defect(state, defect)
        await self.show_as_edit(callback, state)
