import logging
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import STATUS_LABEL
from apps.bot.keyboards.tasks import status_confirm_keyboard, status_picker_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.utils.screens import send_screen
from apps.bot.utils.unregistered import refuse_unregistered

from .card import load_card, show_card
from .render import render_page
from .text import build_status_confirm_text, build_status_pick_text

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import StatusAskCB, StatusPickCB, StatusSetCB
    from apps.core.models import Employee

logger = logging.getLogger(__name__)


async def show_status_picker(
    callback: CallbackQuery, callback_data: StatusPickCB, employee: Employee | None
) -> None:
    """Offer the statuses this defect may move to."""
    card = await load_card(callback, callback_data, employee)

    if card is None:
        return

    send = callback.message.edit_text

    if not card.targets:
        await callback.answer(str(M.STATUS_CHANGE_REFUSED), show_alert=True)
        await show_card(send, card, callback_data.page)
        return

    await callback.answer()

    await send_screen(
        send,
        **build_status_pick_text(card).as_kwargs(),
        reply_markup=status_picker_keyboard(
            card.defect.pk, card.targets, callback_data.page
        ),
    )


async def ask_status_confirmation(
    callback: CallbackQuery, callback_data: StatusAskCB, employee: Employee | None
) -> None:
    """Ask before moving the defect to the picked status."""
    card = await load_card(callback, callback_data, employee)

    if card is None:
        return

    send = callback.message.edit_text

    if callback_data.status not in card.targets:
        await callback.answer(str(M.STATUS_CHANGE_REFUSED), show_alert=True)
        await show_card(send, card, callback_data.page)
        return

    await callback.answer()

    await send_screen(
        send,
        **build_status_confirm_text(card.defect, callback_data.status).as_kwargs(),
        reply_markup=status_confirm_keyboard(
            card.defect.pk, callback_data.status, callback_data.page
        ),
    )


async def set_defect_status(
    callback: CallbackQuery, callback_data: StatusSetCB, employee: Employee | None
) -> None:
    """Save the confirmed status and show the card again."""
    if not employee:
        await refuse_unregistered(callback)
        return

    try:
        card = await services.update_defect_status(
            callback_data.defect_id, callback_data.status, employee=employee
        )
    except Exception:
        logger.exception("Failed to set status on defect %s", callback_data.defect_id)
        await callback.answer(str(M.STATUS_CHANGE_FAILED), show_alert=True)
        return

    if card is None:
        await callback.answer(str(M.STATUS_CHANGE_REFUSED), show_alert=True)
        card = await services.get_defect_card(
            callback_data.defect_id, employee=employee
        )
    else:
        await callback.answer(
            str(M.STATUS_CHANGED).format(status=str(STATUS_LABEL[callback_data.status]))
        )

    send = callback.message.edit_text

    if card is None:
        await render_page(send, employee, callback_data.page)
        return

    await show_card(send, card, callback_data.page)
