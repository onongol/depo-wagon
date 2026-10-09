import logging
from typing import TYPE_CHECKING

from aiogram import Dispatcher
from aiogram.fsm.scene import SceneRegistry

from apps.bot.errors import error_handler
from apps.bot.handlers.defect.scenes import FLOW_SCENES
from apps.bot.handlers.router import get_routers
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
    dp = Dispatcher(storage=storage, events_isolation=events_isolation)

    # Lookup and the `scenes` argument: the flow router places the scene routers
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

    dp.include_routers(*get_routers())

    logger.info("Dispatcher created.")
    return dp
