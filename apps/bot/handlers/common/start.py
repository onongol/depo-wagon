import html
import logging
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import LinkStatus
from apps.bot.keyboards.common import link_confirm_keyboard
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram.filters import CommandObject
    from aiogram.types import CallbackQuery, Message

    from apps.bot.callback_data import LinkConfirmCB
    from apps.core.models import Employee

logger = logging.getLogger(__name__)

_LINK_STATUS_TEXT = {
    LinkStatus.INVALID_TOKEN: M.LINK_TOKEN_INVALID,
    LinkStatus.NO_EMPLOYEE: M.LINK_NO_EMPLOYEE,
    LinkStatus.ALREADY_LINKED: M.LINK_ALREADY_TAKEN,
}


def _error_text(status: LinkStatus):
    """Never leave the chat without an answer, and say so in the log."""
    text = _LINK_STATUS_TEXT.get(status)
    if text is None:
        logger.error("Link status %s has no message", status)
        return M.SESSION_ERROR
    return text


async def show_welcome_menu(message: Message, employee) -> None:
    """Send the main menu greeting to the user."""
    await message.answer(
        str(M.WELCOME_MENU).format(
            full_name=html.escape(employee.full_name),
            role=employee.get_role_display(),
        ),
        parse_mode=M.PARSE_MODE,
        reply_markup=main_menu_keyboard(),
    )


async def start(message: Message, employee: Employee | None) -> None:
    """A bare /start with no token, which is just "who am I".

    An unattached chat is told to go and connect from the web app, because this
    bot cannot establish anybody's identity on its own.
    """
    if employee:
        await show_welcome_menu(message, employee)
        return

    await message.answer(
        str(M.NOT_CONNECTED).format(site_url=services.get_connect_url()),
        parse_mode=M.PARSE_MODE,
    )


async def start_with_link(message: Message, command: CommandObject) -> None:
    """/start from a deep link: spend the token, then ask before attaching.

    Telegram passes the payload of a ``t.me/<bot>?start=<token>`` deep link as
    the argument to /start, which is how the web app hands this chat a token it
    issued for an already-authenticated employee. There is nothing to verify
    here: the web session established who they are before the token existed.

    Nothing is attached here. A deep link can be forwarded, so the chat that
    followed it is asked to confirm out loud which account it is about to take
    over. Spending the token first keeps it single-use while that question
    waits for an answer.
    """
    employee, status = await services.resolve_link_token(command.args)
    if status is not LinkStatus.OK:
        await message.answer(str(_error_text(status)), parse_mode=M.PARSE_MODE)
        return

    await services.remember_pending_link(message.from_user.id, employee.pk)
    await message.answer(
        str(M.LINK_CONFIRM).format(full_name=html.escape(employee.full_name)),
        parse_mode=M.PARSE_MODE,
        reply_markup=link_confirm_keyboard(employee.pk),
    )


async def confirm_link(callback: CallbackQuery, callback_data: LinkConfirmCB) -> None:
    """Attach the chat, if it still holds the offer that named this employee."""
    await callback.answer()

    employee_id = callback_data.employee_id
    try:
        claimed = await services.claim_pending_link(callback.from_user.id, employee_id)
    except Exception:
        logger.exception("Claiming the offer for employee %s failed", employee_id)
        await callback.message.edit_text(str(M.SESSION_ERROR))
        return

    if not claimed:
        logger.warning(
            "Chat %s confirmed employee %s while holding no such offer",
            callback.from_user.id,
            employee_id,
        )
        await callback.message.edit_text(
            str(M.LINK_CONFIRM_EXPIRED), parse_mode=M.PARSE_MODE
        )
        return

    try:
        employee, status = await services.attach_telegram(
            employee_id, callback.from_user.id
        )
    except Exception:
        logger.exception("Attaching a chat to employee %s failed", employee_id)
        await callback.message.edit_text(str(M.SESSION_ERROR))
        return

    if status is not LinkStatus.OK:
        await callback.message.edit_text(
            str(_error_text(status)), parse_mode=M.PARSE_MODE
        )
        return

    await callback.message.edit_text(str(M.LINK_OK), parse_mode=M.PARSE_MODE)
    await show_welcome_menu(callback.message, employee)


async def cancel_link(callback: CallbackQuery) -> None:
    """Drop a link the person declined."""
    await callback.answer()
    try:
        await services.forget_pending_link(callback.from_user.id)
    except Exception:
        logger.exception("Dropping the pending link failed")
    await callback.message.edit_text(str(M.LINK_CANCELLED), parse_mode=M.PARSE_MODE)
