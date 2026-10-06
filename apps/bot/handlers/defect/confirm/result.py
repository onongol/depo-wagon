from typing import TYPE_CHECKING

from apps.bot.handlers.defect.text import build_result_messages
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.utils.screens import take_down

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.types import Message
    from aiogram.utils.formatting import Text

    from apps.bot.user_data import AIResult


async def send_result(
    bot: Bot, progress: Message, fields: list[Text], ai_result: AIResult | None
) -> None:
    """The result replaces the progress message; only a new one brings the menu back."""
    first, *rest = build_result_messages(fields, ai_result)
    await progress.answer(**first.as_kwargs(), reply_markup=main_menu_keyboard())
    await take_down(bot, [progress.chat.id, progress.message_id])

    for text in rest:
        await progress.answer(**text.as_kwargs())
