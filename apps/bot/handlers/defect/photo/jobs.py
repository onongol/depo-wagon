"""The album debounce.

Telegram delivers an album as N separate updates sharing a media_group_id.
Each photo is appended immediately — a crash mid-album must lose none of them —
and only the acknowledgement is debounced, so the user gets one summary rather
than N.

PTB did this with JobQueue, which aiogram has no equivalent for. This is a
direct transcription: one asyncio task per user, cancelled and rescheduled by
each arriving photo, so only the one scheduled by the last photo survives.

An album middleware would not do. It buffers the updates and calls the handler
once, which would delay the appends and lose the whole album on a crash; and it
needs concurrent update handling, which this bot deliberately does not use.
"""

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramAPIError

from apps.bot.callback_data import CB_PHOTO_SKIP
from apps.bot.constants import UD_LAST_PHOTO_MSG
from apps.bot.fsm import load_defect, user_lock
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

FLUSH_DELAY = 0.5

_flush_tasks: dict[int, asyncio.Task] = {}


async def clear_last_photo_keyboard(bot: Bot, state: FSMContext) -> None:
    """Remove the inline keyboard from the previous photo-count message."""
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


def schedule_flush(bot: Bot, state: FSMContext, *, chat_id: int, user_id: int) -> None:
    """Cancel any pending acknowledgement for this user and schedule a new one."""
    pending = _flush_tasks.pop(user_id, None)
    if pending is not None:
        pending.cancel()

    _flush_tasks[user_id] = asyncio.create_task(
        _flush_after(bot, state, chat_id=chat_id, user_id=user_id)
    )


async def _flush_after(
    bot: Bot, state: FSMContext, *, chat_id: int, user_id: int
) -> None:
    await asyncio.sleep(FLUSH_DELAY)
    try:
        await flush_media_group(bot, state, chat_id=chat_id, user_id=user_id)
    finally:
        _flush_tasks.pop(user_id, None)


async def flush_media_group(
    bot: Bot, state: FSMContext, *, chat_id: int, user_id: int
) -> None:
    """Acknowledge the album once, with the count collected so far.

    Holds the user's lock. Updates are handled one at a time, but this runs as
    a background task and makes two network calls between reading and writing
    state — a photo arriving in that window would otherwise lose its file_id.
    """
    async with user_lock(user_id):
        defect = await load_defect(state)
        count = len(defect.photo_file_ids) if defect else 0

        await clear_last_photo_keyboard(bot, state)
        msg = await bot.send_message(
            chat_id=chat_id,
            text=str(M.PHOTO_RECEIVED).format(count=count),
            reply_markup=skip_keyboard(CB_PHOTO_SKIP),
        )
        await state.update_data({UD_LAST_PHOTO_MSG: [msg.chat.id, msg.message_id]})


async def cancel_pending_flushes() -> None:
    """Drop scheduled acknowledgements on shutdown.

    Without this the loop closes with tasks still pending and asyncio complains
    on every stop.
    """
    tasks = list(_flush_tasks.values())
    _flush_tasks.clear()
    for task in tasks:
        task.cancel()
    for task in tasks:
        with contextlib.suppress(asyncio.CancelledError):
            await task
