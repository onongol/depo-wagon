import logging
from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher, Router
from aiogram.types import BotCommand, MenuButtonCommands
from django.utils.translation import gettext_lazy as _

from apps.bot.filters import PRIVATE_CALLBACK, PRIVATE_CHAT
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
    """Every private-chat router, in the order updates reach them. Load-bearing:

    - start first, so the link buttons work mid-flow instead of hitting its catch-all;
    - cancel ahead of every conversation, so /cancel ends everything by order alone;
    - the defect entry ahead of support and ai_chat, so New Defect leaves them for a form;
    - tasks ahead of support and ai_chat, so Open Defects leaves them for the list;
    - support ahead of ai_chat and help, so their buttons cancel it, not get relayed;
    - help after the conversations, so Help inside the AI chat reaches its fallback;
    - stale last: it sees only what nothing else claimed.
    """
    from apps.bot.handlers.ai_chat.router import get_ai_chat_router
    from apps.bot.handlers.common.router import (
        get_cancel_router,
        get_help_router,
        get_stale_router,
    )
    from apps.bot.handlers.defect.router import (
        get_defect_entry_router,
        get_defect_flow_router,
    )
    from apps.bot.handlers.start.router import get_start_router
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


def _private_router() -> Router:
    """Everything a private chat reaches. The chat-type filters sit here once.

    Callbacks too: no router puts buttons in a group, so a tap there is forged.
    """
    router = Router(name="private")
    router.message.filter(PRIVATE_CHAT)
    router.callback_query.filter(PRIVATE_CALLBACK)
    router.include_routers(*_routers())
    return router


def make_dispatcher(
    storage: BaseStorage, events_isolation: BaseEventIsolation
) -> Dispatcher:
    from apps.bot.errors import error_handler
    from apps.bot.handlers.support.router import get_support_group_router

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

    # Disjoint by chat, so neither can shadow the other
    private = _private_router()
    dp.include_routers(private, get_support_group_router())

    logger.info("Dispatcher created with %s private routers.", len(private.sub_routers))
    return dp
