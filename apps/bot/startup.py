from typing import TYPE_CHECKING

from aiogram.types import BotCommand, MenuButtonCommands
from django.utils.translation import gettext_lazy as _

from apps.bot.messages import BotMessages as M

if TYPE_CHECKING:
    from aiogram import Bot

_BOT_COMMANDS = [
    ("start", _("Start")),
    ("new_defect", _("Register a defect")),
    ("my_tasks", _("Open defects")),
    ("ask", _("AI Assistant")),
    ("support", _("Ask the support team")),
    ("help", _("Help")),
    ("cancel", _("Cancel the current action")),
]


async def on_startup(bot: Bot) -> None:
    """Publish commands, descriptions and the Menu button as stable entry points."""
    commands = [
        BotCommand(command=command, description=str(description))
        for command, description in _BOT_COMMANDS
    ]
    await bot.set_my_commands(commands)
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    await bot.set_my_description(str(M.BOT_DESCRIPTION))
    await bot.set_my_short_description(str(M.BOT_SHORT_DESCRIPTION))
