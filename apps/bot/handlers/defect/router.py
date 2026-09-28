"""Routers for defect registration.

Disjoint by state: the entry answers only outside DefectSG, and inside it the
flow asks whether to continue or start over, so a running form is never wiped
without the user choosing to.

Mid-migration to Scenes: a step that is a Scene lives in its own router, ahead
of the steps still written as plain handlers, and carries the shared handlers
itself. The plain ones share theirs through the running block below.
"""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter

from apps.bot.callback_data import (
    CB_CANCEL,
    CB_DEFECT_CONTINUE,
    CB_DEFECT_RESTART,
    ConfirmCB,
    EditCB,
    VerdictCB,
)
from apps.bot.constants import BTN_NEW_DEFECT
from apps.bot.keyboards.menu import MENU_TEXTS
from apps.bot.middlewares import DefectFormMiddleware
from apps.bot.states import DefectSG

from .cancel import cancel_defect_button, stale_callback
from .confirm import confirm_defect
from .edit import start_edit
from .restart import continue_defect, menu_button_mid_flow, restart_defect
from .scene import ask_about_the_open_form
from .scenes import DEFECT_SCENES
from .start import new_defect_start
from .verdict import receive_employee_verdict


def get_defect_flow_router() -> Router:
    """Every step: the Scenes first, then the plain steps."""
    router = Router(name="defect_flow")

    # Outer, so no step is reached with a form that is stale or gone
    router.message.outer_middleware(DefectFormMiddleware())
    router.callback_query.outer_middleware(DefectFormMiddleware())

    router.include_routers(
        *(scene.as_router() for scene in DEFECT_SCENES), _plain_steps_router()
    )
    return router


def _plain_steps_router() -> Router:
    """Every step not yet a Scene, filtered by the state it belongs to."""
    router = Router(name="defect_plain_steps")
    msg = router.message.register
    cb = router.callback_query.register

    # Menu buttons ahead of every step; a text step would take one for an answer
    running = StateFilter(DefectSG)
    msg(ask_about_the_open_form, running, Command("new_defect"))
    msg(ask_about_the_open_form, running, F.text == str(BTN_NEW_DEFECT))
    msg(menu_button_mid_flow, running, F.text.in_(MENU_TEXTS))
    msg(
        menu_button_mid_flow,
        running,
        Command("start", "my_tasks", "ask", "support", "help"),
    )
    cb(continue_defect, running, F.data == CB_DEFECT_CONTINUE)
    cb(restart_defect, running, F.data == CB_DEFECT_RESTART)

    cb(start_edit, StateFilter(DefectSG.confirm), EditCB.filter())
    # Split so that cancelling never loads the employee
    cb(
        cancel_defect_button,
        StateFilter(DefectSG.confirm),
        ConfirmCB.filter(~F.confirmed),
    )
    cb(confirm_defect, StateFilter(DefectSG.confirm), ConfirmCB.filter(F.confirmed))

    cb(
        receive_employee_verdict,
        StateFilter(DefectSG.employee_verdict),
        VerdictCB.filter(),
    )

    # Fallbacks: the Cancel button, then any other tap. /cancel is the global router's.
    cb(cancel_defect_button, StateFilter(DefectSG), F.data == CB_CANCEL)
    cb(stale_callback, StateFilter(DefectSG))

    return router


def get_defect_entry_router() -> Router:
    """The two ways in, outside a running form."""
    router = Router(name="defect_entry")
    router.message.filter(~StateFilter(DefectSG))
    router.message.register(new_defect_start, Command("new_defect"))
    router.message.register(new_defect_start, F.text == str(BTN_NEW_DEFECT))
    return router
