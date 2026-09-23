import html
from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import LinkStatus
from apps.bot.handlers.common.link_errors import get_link_error_message
from apps.bot.keyboards.common import link_confirm_keyboard
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram.filters import CommandObject
    from aiogram.types import CallbackQuery, Message

    from apps.bot.callback_data import LinkConfirmCB
    from apps.core.models import Employee


async def show_welcome_menu(message: Message, employee) -> None:
    await message.answer(
        str(M.WELCOME_MENU).format(
            full_name=html.escape(employee.full_name),
            role=employee.get_role_display(),
        ),
        parse_mode=M.PARSE_MODE,
        reply_markup=main_menu_keyboard(),
    )


async def start(message: Message, employee: Employee | None) -> None:
    if employee:
        await show_welcome_menu(message, employee)
        return

    await message.answer(
        str(M.NOT_CONNECTED).format(site_url=services.get_connect_url()),
        parse_mode=M.PARSE_MODE,
    )


async def start_with_link(message: Message, command: CommandObject) -> None:
    employee, status = await services.resolve_link_token(command.args)

    if status is not LinkStatus.OK:
        await message.answer(
            str(get_link_error_message(status)), parse_mode=M.PARSE_MODE
        )
        return

    await services.remember_pending_link(message.from_user.id, employee.pk)

    await message.answer(
        str(M.LINK_CONFIRM).format(full_name=html.escape(employee.full_name)),
        parse_mode=M.PARSE_MODE,
        reply_markup=link_confirm_keyboard(employee.pk),
    )


async def confirm_link(callback: CallbackQuery, callback_data: LinkConfirmCB) -> None:
    await callback.answer()

    employee, status = await services.complete_telegram_link(
        telegram_id=callback.from_user.id, employee_id=callback_data.employee_id
    )

    if status is not LinkStatus.OK:
        await callback.message.edit_text(
            str(get_link_error_message(status)), parse_mode=M.PARSE_MODE
        )
        return

    await callback.message.edit_text(str(M.LINK_OK), parse_mode=M.PARSE_MODE)
    await show_welcome_menu(callback.message, employee)


async def cancel_link(callback: CallbackQuery) -> None:
    await callback.answer()
    await services.forget_pending_link(callback.from_user.id)
    await callback.message.edit_text(str(M.LINK_CANCELLED), parse_mode=M.PARSE_MODE)
