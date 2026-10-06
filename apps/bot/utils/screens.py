import logging
from contextlib import suppress
from typing import TYPE_CHECKING, Any

from aiogram.exceptions import TelegramBadRequest

from apps.bot.constants import UD_SCREEN
from apps.bot.fsm import drop_keys

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import (
        CallbackQuery,
        InlineKeyboardMarkup,
        MaybeInaccessibleMessageUnion,
        Message,
        ReplyKeyboardMarkup,
    )

logger = logging.getLogger(__name__)


def _is_not_modified(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in exc.message.lower()


def _is_uneditable(exc: TelegramBadRequest) -> bool:
    """The message is gone or too old; any other 400 is about the screen itself."""
    msg = exc.message.lower()
    return "message to edit not found" in msg or "message can't be edited" in msg


async def edit_or_send(
    callback: CallbackQuery,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
    **kwargs: Any,
) -> None:
    """Replace the button's message, or send the screen anew when it can't be.

    Edits by chat and message id, so an InaccessibleMessage is tried too. Only an
    inline keyboard can ride an edit; a reply keyboard needs its own message.
    """
    message = callback.message
    if message is None:
        await callback.bot.send_message(
            callback.from_user.id, reply_markup=reply_markup, **kwargs
        )
        return

    try:
        await callback.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=reply_markup,
            **kwargs,
        )
    except TelegramBadRequest as exc:
        if _is_not_modified(exc):
            return
        if not _is_uneditable(exc):
            raise
        logger.info("Message refused the edit, sending anew: %s", exc.message)
    else:
        return

    await message.answer(reply_markup=reply_markup, **kwargs)


async def answer_anew(
    callback: CallbackQuery, *, reply_markup: ReplyKeyboardMarkup, **kwargs: Any
) -> None:
    """Strip the button's message of its keyboard and answer in a new one.

    For a reply keyboard, which no edit can carry. A 400 on the strip means the
    buttons are already gone, which is all it was for.
    """
    message = callback.message
    if message is None:
        await callback.bot.send_message(
            callback.from_user.id, reply_markup=reply_markup, **kwargs
        )
        return

    with suppress(TelegramBadRequest):
        await callback.bot.edit_message_reply_markup(
            chat_id=message.chat.id, message_id=message.message_id, reply_markup=None
        )

    await message.answer(reply_markup=reply_markup, **kwargs)


async def delete_input(message: Message) -> None:
    """Take what the user sent off the chat; a 400 means it is gone already."""
    with suppress(TelegramBadRequest):
        await message.delete()


async def show_screen(
    bot: Bot,
    state: FSMContext,
    chat_id: int,
    *,
    tapped: MaybeInaccessibleMessageUnion | None = None,
    below: bool = False,
    **kwargs: Any,
) -> None:
    """Draw the form's one screen: edited in place, or sent anew at the bottom.

    below is for input left in the chat: the screen goes under it and the old
    one is taken down. With no screen stored yet, a tap adopts its message.
    kwargs are the screen's text and its inline keyboard, as for send_message.
    """
    screen = (await state.get_data()).get(UD_SCREEN)
    if screen is None and tapped is not None:
        screen = [tapped.chat.id, tapped.message_id]
        await state.update_data({UD_SCREEN: screen})

    if screen and not below and await _edit(bot, screen, kwargs):
        return

    sent = await bot.send_message(chat_id, **kwargs)
    await state.update_data({UD_SCREEN: [chat_id, sent.message_id]})
    if screen and below:
        await take_down(bot, screen)


async def close_screen(bot: Bot, state: FSMContext) -> None:
    """Take the form's screen off the chat as the form ends."""
    if screen := (await state.get_data()).get(UD_SCREEN):
        await take_down(bot, screen)
    await drop_keys(state, UD_SCREEN)


async def take_down(bot: Bot, screen: list[int]) -> None:
    """Delete a screen, or strip its buttons where Telegram refuses the delete."""
    chat_id, message_id = screen
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        with suppress(TelegramBadRequest):
            await bot.edit_message_reply_markup(
                chat_id=chat_id, message_id=message_id, reply_markup=None
            )


async def _edit(bot: Bot, screen: list[int], kwargs: dict[str, Any]) -> bool:
    """False when the screen is gone or too old to edit, so it is sent anew."""
    chat_id, message_id = screen
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, **kwargs)
    except TelegramBadRequest as exc:
        if _is_not_modified(exc):
            return True
        if not _is_uneditable(exc):
            raise
        logger.info("The screen refused the edit, sending anew: %s", exc.message)
        return False
    return True
