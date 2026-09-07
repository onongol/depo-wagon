from typing import TYPE_CHECKING

from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from telegram import Message


async def show_welcome_menu(message: Message, employee) -> None:
    """Send the main menu greeting to the user."""
    await message.reply_text(
        str(M.WELCOME_MENU).format(
            full_name=employee.full_name,
            role=employee.get_role_display(),
        ),
        parse_mode=M.PARSE_MODE,
        reply_markup=main_menu_keyboard(employee.role),
    )
