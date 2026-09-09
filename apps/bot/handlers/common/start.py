import html
import logging
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import LinkStatus
from apps.bot.keyboards.common import link_confirm_keyboard
from apps.bot.messages import BotMessages as M

from .utils import show_welcome_menu

if TYPE_CHECKING:
    from aiogram.filters import CommandObject
    from aiogram.types import CallbackQuery, Message

    from apps.bot.callback_data import LinkConfirmCB

logger = logging.getLogger(__name__)

_RESOLVE_ERROR_TEXT = {
    LinkStatus.INVALID_TOKEN: M.LINK_TOKEN_INVALID,
    LinkStatus.NO_EMPLOYEE: M.LINK_NO_EMPLOYEE,
}

_ATTACH_ERROR_TEXT = {
    LinkStatus.NO_EMPLOYEE: M.LINK_NO_EMPLOYEE,
    LinkStatus.ALREADY_LINKED: M.LINK_ALREADY_TAKEN,
}


def _error_text(texts: dict, status: LinkStatus):
    """Never leave the chat without an answer, and say so in the log."""
    text = texts.get(status)
    if text is None:
        logger.error("Link status %s has no message on this path", status)
        return M.SESSION_ERROR
    return text


async def start(message: Message, command: CommandObject) -> None:
    """Entry point, and the only place a Telegram account gets attached.

    Telegram passes the payload of a ``t.me/<bot>?start=<token>`` deep link as
    the argument to /start, which is how the web app hands this chat a token it
    issued for an already-authenticated employee. There is nothing to verify
    here: the web session established who they are before the token existed.

    A bare /start with no token is just "who am I" — an unattached chat is told
    to go and connect from the web app, because this bot cannot establish
    anybody's identity on its own.
    """
    if command.args:
        await _handle_link_token(message, command.args)
        return

    try:
        employee = await services.get_employee_by_telegram_id(message.from_user.id)
    except Exception:
        logger.exception("Employee lookup failed for the incoming chat")
        await message.answer(str(M.SESSION_ERROR))
        return

    if employee:
        await show_welcome_menu(message, employee)
        return

    await message.answer(
        str(M.NOT_CONNECTED).format(site_url=services.get_connect_url()),
        parse_mode=M.PARSE_MODE,
    )


async def _handle_link_token(message: Message, token: str) -> None:
    """Spend the token, then ask before attaching anything.

    Nothing is written here. A deep link can be forwarded, so the chat that
    followed it is asked to confirm out loud which account it is about to take
    over. Spending the token first keeps it single-use while that question
    waits for an answer.
    """
    try:
        employee, status = await services.resolve_link_token(token)
    except Exception:
        logger.exception("Resolving a link token failed")
        await message.answer(str(M.SESSION_ERROR))
        return

    if status is not LinkStatus.OK:
        text = _error_text(_RESOLVE_ERROR_TEXT, status)
        await message.answer(str(text), parse_mode=M.PARSE_MODE)
        return

    await message.answer(
        str(M.LINK_CONFIRM).format(full_name=html.escape(employee.full_name)),
        parse_mode=M.PARSE_MODE,
        reply_markup=link_confirm_keyboard(employee.pk),
    )


async def confirm_link(callback: CallbackQuery, callback_data: LinkConfirmCB) -> None:
    """Attach the chat now that the person has agreed to it."""
    await callback.answer()

    employee_id = callback_data.employee_id
    try:
        employee, status = await services.attach_telegram(
            employee_id, callback.from_user.id
        )
    except Exception:
        logger.exception("Attaching a chat to employee %s failed", employee_id)
        await callback.message.edit_text(str(M.SESSION_ERROR))
        return

    if status is not LinkStatus.OK:
        text = _error_text(_ATTACH_ERROR_TEXT, status)
        await callback.message.edit_text(str(text), parse_mode=M.PARSE_MODE)
        return

    await callback.message.edit_text(str(M.LINK_OK), parse_mode=M.PARSE_MODE)
    await show_welcome_menu(callback.message, employee)


async def cancel_link(callback: CallbackQuery) -> None:
    """Drop a link the person declined."""
    await callback.answer()
    await callback.message.edit_text(str(M.LINK_CANCELLED), parse_mode=M.PARSE_MODE)
