from typing import TYPE_CHECKING

from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery


async def refuse_unregistered(callback: CallbackQuery) -> None:
    """A stale keyboard outlives deactivation; it must not show anyone's defects."""
    await callback.answer()
    await callback.message.edit_text(str(M.NOT_REGISTERED), parse_mode=M.PARSE_MODE)
