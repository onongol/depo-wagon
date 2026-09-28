from aiogram import F, Router
from aiogram.filters import Command, StateFilter

from apps.bot.callback_data import CB_NOOP
from apps.bot.constants import BTN_CANCEL, BTN_HELP
from apps.bot.states import ALL_GROUPS

from .cancel import cancel
from .help import help_command
from .stale import noop_button, stale_button, unhandled_message


def get_cancel_router() -> Router:
    """/cancel and Cancel, ahead of every flow: they win by order, not by filters."""
    router = Router(name="cancel")
    router.message.register(cancel, Command("cancel"))
    router.message.register(cancel, F.text == str(BTN_CANCEL))
    return router


def get_help_router() -> Router:
    """/help, after the flows so their Help button reaches the flow, not help."""
    router = Router(name="help")
    router.message.register(help_command, Command("help"))
    router.message.register(help_command, F.text == str(BTN_HELP))
    return router


def get_stale_router() -> Router:
    """What nothing else claimed; last. The spacer precedes the unfiltered fallback.

    Messages only outside every known state, so a sticker at the photo step
    leaves the form alone.
    """
    router = Router(name="stale")
    router.callback_query.register(noop_button, F.data == CB_NOOP)
    router.callback_query.register(stale_button)
    router.message.register(unhandled_message, ~StateFilter(*ALL_GROUPS))
    return router
