from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.handlers.common.utils import send_screen
from apps.bot.keyboards.tasks import defect_card_keyboard
from apps.bot.messages import BotMessages as M

from .render import render_page
from .text import build_card_text
from .utils import refuse_unregistered

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import DefectCardCB, DefectRef, StatusRef
    from apps.bot.services.defect_card import DefectCard
    from apps.core.models import Employee


async def show_card(
    send: Callable[..., Awaitable], card: DefectCard, page: int
) -> None:
    await send_screen(
        send,
        **build_card_text(card).as_kwargs(),
        reply_markup=defect_card_keyboard(
            card.defect.pk, page, can_change=bool(card.targets)
        ),
    )


async def load_card(
    callback: CallbackQuery,
    callback_data: DefectRef | StatusRef,
    employee: Employee | None,
) -> DefectCard | None:
    """The card a tap points at, or None once the tap has been answered without one."""
    if not employee:
        await refuse_unregistered(callback)
        return None

    card = await services.get_defect_card(callback_data.defect_id, employee=employee)

    if card is None:
        await callback.answer(str(M.DEFECT_UNAVAILABLE), show_alert=True)
        await render_page(callback.message.edit_text, employee, callback_data.page)

    return card


async def show_defect_card(
    callback: CallbackQuery, callback_data: DefectCardCB, employee: Employee | None
) -> None:
    """Open one defect from the list."""
    card = await load_card(callback, callback_data, employee)

    if card is None:
        return

    await callback.answer()
    await show_card(callback.message.edit_text, card, callback_data.page)
