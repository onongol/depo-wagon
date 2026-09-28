from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery


async def stale_callback(callback: CallbackQuery) -> None:
    """Silently absorb any callback no step in this flow claimed.

    Registered last inside the flow router, reproducing PTB's pattern-less
    fallback: while a defect is in progress an out-of-order tap dies quietly
    rather than getting the expired-button reply.
    """
    await callback.answer()
