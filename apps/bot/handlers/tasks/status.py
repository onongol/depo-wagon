import logging
from functools import partial
from typing import TYPE_CHECKING

from aiogram import flags

from apps.bot import services
from apps.bot.keyboards.tasks import status_confirm_keyboard, status_picker_keyboard
from apps.bot.utils.screens import edit_or_send

from .card import load_card, show_card
from .render import render_page
from .text import (
    build_status_changed_toast,
    build_status_confirm_text,
    build_status_failed_toast,
    build_status_pick_text,
    build_status_refused_toast,
)

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import StatusAskCB, StatusPickCB, StatusSetCB
    from apps.core.models import Employee

logger = logging.getLogger(__name__)


@flags.registered
async def show_status_picker(
    callback: CallbackQuery, callback_data: StatusPickCB, employee: Employee
) -> None:
    """Offer the statuses this defect may move to."""
    card = await load_card(callback, callback_data, employee)

    if card is None:
        return

    send = partial(edit_or_send, callback)

    if not card.targets:
        await callback.answer(build_status_refused_toast(), show_alert=True)
        await show_card(send, card, callback_data.page)
        return

    await callback.answer()

    await send(
        **build_status_pick_text(card).as_kwargs(),
        reply_markup=status_picker_keyboard(
            card.defect.pk, card.targets, callback_data.page
        ),
    )


@flags.registered
async def ask_status_confirmation(
    callback: CallbackQuery, callback_data: StatusAskCB, employee: Employee
) -> None:
    """Ask before moving the defect to the picked status."""
    card = await load_card(callback, callback_data, employee)

    if card is None:
        return

    send = partial(edit_or_send, callback)

    if callback_data.status not in card.targets:
        await callback.answer(build_status_refused_toast(), show_alert=True)
        await show_card(send, card, callback_data.page)
        return

    await callback.answer()

    await send(
        **build_status_confirm_text(card.defect, callback_data.status).as_kwargs(),
        reply_markup=status_confirm_keyboard(
            card.defect.pk, callback_data.status, callback_data.page
        ),
    )


@flags.registered
async def set_defect_status(
    callback: CallbackQuery, callback_data: StatusSetCB, employee: Employee
) -> None:
    """Save the confirmed status and show the card again."""
    try:
        card = await services.update_defect_status(
            callback_data.defect_id, callback_data.status, employee=employee
        )
    except Exception:
        logger.exception("Failed to set status on defect %s", callback_data.defect_id)
        await callback.answer(build_status_failed_toast(), show_alert=True)
        return

    if card is None:
        await callback.answer(build_status_refused_toast(), show_alert=True)
        card = await services.get_defect_card(
            callback_data.defect_id, employee=employee
        )
    else:
        await callback.answer(build_status_changed_toast(callback_data.status))

    send = partial(edit_or_send, callback)

    if card is None:
        await render_page(send, employee, callback_data.page)
        return

    await show_card(send, card, callback_data.page)
