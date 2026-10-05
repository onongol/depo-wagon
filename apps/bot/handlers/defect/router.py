from aiogram import F, Router
from aiogram.filters import Command, StateFilter

from apps.bot.constants import BTN_NEW_DEFECT
from apps.bot.middlewares import DefectFormMiddleware
from apps.bot.states import DefectSG

from .scenes import FLOW_SCENES
from .start import new_defect_start


def get_defect_flow_router() -> Router:
    """Every state of the form, each a scene."""
    router = Router(name="defect_flow")

    # Outer, so no step is reached with a form that is stale or gone
    router.message.outer_middleware(DefectFormMiddleware())
    router.callback_query.outer_middleware(DefectFormMiddleware())

    router.include_routers(*(scene.as_router() for scene in FLOW_SCENES))
    return router


def get_defect_entry_router() -> Router:
    """The two ways in, outside a running form."""
    router = Router(name="defect_entry")
    router.message.filter(~StateFilter(DefectSG))
    router.message.register(new_defect_start, Command("new_defect"))
    router.message.register(new_defect_start, F.text == str(BTN_NEW_DEFECT))
    return router
