from typing import TYPE_CHECKING

from apps.bot.utils.unregistered import build_not_registered_text

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery


async def refuse_unregistered(callback: CallbackQuery) -> None:
    """A stale keyboard outlives deactivation; it must not show anyone's defects."""
    await callback.answer()
    await callback.message.edit_text(**build_not_registered_text().as_kwargs())
