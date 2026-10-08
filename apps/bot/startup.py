from typing import TYPE_CHECKING

from aiogram.types import BotCommand, MenuButtonCommands
from aiogram.utils.formatting import Text, as_list
from django.utils.translation import gettext_lazy as _

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


def build_bot_description_text() -> Text:
    return as_list(
        _(
            "Register wagon defects step by step: wagon, department, node, type and "
            "severity, with photos and measurements, plus an instant AI assessment."
        ),
        _("Tap the Menu button or send /start to begin."),
        sep="\n\n",
    )


def build_bot_short_description_text() -> Text:
    return Text(
        _("Register and track wagon defects with photos, measurements and AI analysis.")
    )


async def on_startup(bot: Bot) -> None:
    """Publish commands, descriptions and the Menu button as stable entry points.

    The descriptions take plain text only, so their entities are dropped.
    """
    commands = [
        BotCommand(command=command, description=str(description))
        for command, description in _BOT_COMMANDS
    ]
    await bot.set_my_commands(commands)
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    await bot.set_my_description(build_bot_description_text().render()[0])
    await bot.set_my_short_description(build_bot_short_description_text().render()[0])
