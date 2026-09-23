from typing import TYPE_CHECKING

from apps.bot.handlers.common.text import build_help_text

if TYPE_CHECKING:
    from aiogram.types import Message


async def help_command(message: Message) -> None:
    """Show available bot commands."""
    await message.answer(**build_help_text().as_kwargs())
