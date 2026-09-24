"""Dispatcher assembly. Replaces the PTB Application builder."""

import logging
from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, MenuButtonCommands
from django.utils.translation import gettext_lazy as _

from apps.bot.messages import BotMessages as M
from apps.bot.middlewares import (
    AiChatTimeoutMiddleware,
    CloseOldConnectionsMiddleware,
    EmployeeMiddleware,
)

if TYPE_CHECKING:
    from aiogram.fsm.storage.base import BaseEventIsolation, BaseStorage

logger = logging.getLogger(__name__)

# Commands shown in the "/" menu and under the always-visible Menu button,
# so users have an entry point even when the START button is gone.
#
# Plain tuples, not BotCommand: aiogram validates on construction, so a lazy
# gettext proxy in here would fail at import rather than at send time. Holding
# the descriptions lazily until on_startup is what keeps them translatable.
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


def _routers() -> list:
    """Every router, in the order updates are offered to them.

    The order is load-bearing and reproduces PTB's registration order:

    - start comes before the conversations, so /start and the account-link
      buttons still work mid-flow;
    - cancel comes right after start, for the same reason but by aiogram's own
      idiom: an unfiltered Command("cancel") ahead of every conversation wins
      by registration order alone, rather than depending on each flow's
      free-text steps filtering it out with NotACommand;
    - each conversation's state-filtered router precedes its own entry points,
      which is how PTB kept an entry point from restarting a running flow;
    - help comes after the conversations, so the Help button pressed inside
      the AI chat reaches that flow's fallback rather than help_command;
    - stale is last, and only sees what nothing else claimed.
    """
    from apps.bot.handlers.ai_chat.router import get_ai_chat_router
    from apps.bot.handlers.common.router import (
        get_cancel_router,
        get_help_router,
        get_stale_router,
        get_start_router,
    )
    from apps.bot.handlers.defect.router import (
        get_defect_entry_router,
        get_defect_flow_router,
    )
    from apps.bot.handlers.support.router import get_support_router
    from apps.bot.handlers.tasks.router import get_tasks_router

    return [
        get_start_router(),
        get_cancel_router(),
        get_defect_flow_router(),
        get_defect_entry_router(),
        get_tasks_router(),
        get_support_router(),
        get_ai_chat_router(),
        get_help_router(),
        get_stale_router(),
    ]


def make_dispatcher(
    storage: BaseStorage, events_isolation: BaseEventIsolation
) -> Dispatcher:
    from apps.bot.errors import error_handler

    dp = Dispatcher(storage=storage, events_isolation=events_isolation)

    # dp.update is the only observer that fires exactly once per Update and
    # ahead of every filter — where PTB closed connections by overriding
    # Application.process_update.
    dp.update.outer_middleware(CloseOldConnectionsMiddleware())

    # Global rather than on the ai_chat router: a router earlier in the chain
    # claiming the update would otherwise leave an expired session standing.
    dp.update.outer_middleware(AiChatTimeoutMiddleware())

    # Inner, so it reaches the handlers of every included router
    employee = EmployeeMiddleware()
    dp.message.middleware(employee)
    dp.callback_query.middleware(employee)

    dp.startup.register(on_startup)
    dp.errors.register(error_handler)

    for router in _routers():
        dp.include_router(router)

    logger.info("Dispatcher created with %s routers.", len(dp.sub_routers))
    return dp
