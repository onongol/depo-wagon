from typing import TYPE_CHECKING

from apps.bot import services
from apps.bot.constants import LinkStatus
from apps.bot.handlers.common.link_errors import get_link_error_message
from apps.bot.handlers.common.text import (
    build_link_cancelled_text,
    build_link_confirm_text,
    build_link_ok_text,
    build_not_connected_text,
    build_welcome_text,
)
from apps.bot.keyboards.common import link_confirm_keyboard
from apps.bot.keyboards.menu import main_menu_keyboard

if TYPE_CHECKING:
    from aiogram.filters import CommandObject
    from aiogram.types import CallbackQuery, Message

    from apps.bot.callback_data import LinkConfirmCB
    from apps.core.models import Employee


async def show_welcome_menu(message: Message, employee) -> None:
    await message.answer(
        **build_welcome_text(employee).as_kwargs(),
        reply_markup=main_menu_keyboard(),
    )


async def start(message: Message, employee: Employee | None) -> None:
    if employee:
        await show_welcome_menu(message, employee)
        return

    await message.answer(
        **build_not_connected_text(services.get_connect_url()).as_kwargs()
    )


async def start_with_link(message: Message, command: CommandObject) -> None:
    employee, status = await services.resolve_link_token(command.args)

    if status is not LinkStatus.OK:
        await message.answer(**get_link_error_message(status).as_kwargs())
        return

    await services.remember_pending_link(message.from_user.id, employee.pk)

    await message.answer(
        **build_link_confirm_text(employee).as_kwargs(),
        reply_markup=link_confirm_keyboard(employee.pk),
    )


async def confirm_link(callback: CallbackQuery, callback_data: LinkConfirmCB) -> None:
    await callback.answer()

    employee, status = await services.complete_telegram_link(
        telegram_id=callback.from_user.id, employee_id=callback_data.employee_id
    )

    if status is not LinkStatus.OK:
        await callback.message.edit_text(**get_link_error_message(status).as_kwargs())
        return

    await callback.message.edit_text(**build_link_ok_text().as_kwargs())
    await show_welcome_menu(callback.message, employee)


async def cancel_link(callback: CallbackQuery) -> None:
    await callback.answer()
    await services.forget_pending_link(callback.from_user.id)
    await callback.message.edit_text(**build_link_cancelled_text().as_kwargs())
