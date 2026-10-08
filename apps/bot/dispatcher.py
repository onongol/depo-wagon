import logging
from typing import TYPE_CHECKING

from aiogram import Dispatcher
from aiogram.fsm.scene import SceneRegistry

from apps.bot.handlers.router import get_private_router
from apps.bot.middlewares import (
    AiChatTimeoutMiddleware,
    CloseOldConnectionsMiddleware,
    EmployeeMiddleware,
)
from apps.bot.startup import on_startup

if TYPE_CHECKING:
    from aiogram.fsm.storage.base import BaseEventIsolation, BaseStorage

logger = logging.getLogger(__name__)


def make_dispatcher(
    storage: BaseStorage, events_isolation: BaseEventIsolation
) -> Dispatcher:
    from apps.bot.errors import error_handler
    from apps.bot.handlers.defect.scenes import FLOW_SCENES
    from apps.bot.handlers.support.router import get_support_group_router

    dp = Dispatcher(storage=storage, events_isolation=events_isolation)

    # Lookup only: the defect flow router places the scene routers in its order
    SceneRegistry(dp, register_on_add=False).add(*FLOW_SCENES)

    # The only observer firing once per update, ahead of every filter
    dp.update.outer_middleware(CloseOldConnectionsMiddleware())

    # Global, so an update claimed before ai_chat still expires its session
    dp.update.outer_middleware(AiChatTimeoutMiddleware())

    # Inner: it reads the matched handler's flags and parameters
    employee = EmployeeMiddleware()
    dp.message.middleware(employee)
    dp.callback_query.middleware(employee)

    dp.startup.register(on_startup)
    dp.errors.register(error_handler)

    # Disjoint by chat, so neither can shadow the other
    private = get_private_router()
    dp.include_routers(private, get_support_group_router())

    logger.info("Dispatcher created with %s private routers.", len(private.sub_routers))
    return dp
