from typing import TYPE_CHECKING

from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram.types import Message


async def help_command(message: Message) -> None:
    """Show available bot commands."""
    await message.answer(str(M.HELP_TEXT), parse_mode=M.PARSE_MODE)
