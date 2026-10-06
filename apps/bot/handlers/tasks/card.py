from functools import partial
from typing import TYPE_CHECKING

from aiogram import flags

from apps.bot import services
from apps.bot.keyboards.tasks import defect_card_keyboard
from apps.bot.utils.screens import edit_or_send

from .render import render_page
from .text import build_card_text, build_defect_unavailable_toast

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import DefectCardCB, DefectRef, StatusRef
    from apps.bot.services.defect_card import DefectCard
    from apps.core.models import Employee


async def show_card(
    send: Callable[..., Awaitable], card: DefectCard, page: int
) -> None:
    await send(
        **build_card_text(card).as_kwargs(),
        reply_markup=defect_card_keyboard(
            card.defect.pk, page, can_change=bool(card.targets)
        ),
    )


async def load_card(
    callback: CallbackQuery,
    callback_data: DefectRef | StatusRef,
    employee: Employee,
) -> DefectCard | None:
    """The card a tap points at, or None once the tap has been answered without one."""
    card = await services.get_defect_card(callback_data.defect_id, employee=employee)

    if card is None:
        await callback.answer(build_defect_unavailable_toast(), show_alert=True)
        await render_page(partial(edit_or_send, callback), employee, callback_data.page)

    return card


@flags.registered
async def show_defect_card(
    callback: CallbackQuery, callback_data: DefectCardCB, employee: Employee
) -> None:
    """Open one defect from the list."""
    card = await load_card(callback, callback_data, employee)

    if card is None:
        return

    await callback.answer()
    await show_card(partial(edit_or_send, callback), card, callback_data.page)
