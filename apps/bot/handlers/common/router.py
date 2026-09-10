"""Routers for the handlers that are not part of any conversation.

Registration stays imperative, as it was under PTB — handlers are plain
functions with no decorators, which is what lets the tests call them directly.
"""

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart

from apps.bot.callback_data import CB_LINK_CANCEL, CB_NOOP, LinkConfirmCB
from apps.bot.constants import BTN_HELP

from .cancel import cancel
from .help import help_command
from .stale import noop_button, stale_button, unhandled_message
from .start import cancel_link, confirm_link, start


def get_start_router() -> Router:
    """/start and the account-link answer.

    Included before every conversation, which is what PTB's registration order
    did: /start mid-flow is answered here and leaves the flow standing.
    """
    router = Router(name="start")
    router.message.register(start, CommandStart())
    router.callback_query.register(confirm_link, LinkConfirmCB.filter())
    router.callback_query.register(cancel_link, F.data == CB_LINK_CANCEL)
    return router


def get_utility_router() -> Router:
    """/help and /cancel.

    Included after the conversations, mirroring PTB's registration order: the
    Help menu button pressed inside the AI chat reaches that flow's own
    fallback, not help_command.
    """
    router = Router(name="utility")
    router.message.register(help_command, Command("help"))
    router.message.register(help_command, F.text == str(BTN_HELP))
    router.message.register(cancel, Command("cancel"))
    return router


def get_stale_router() -> Router:
    """Last resort for updates nothing else claimed. Included last.

    The callback handler carries no filter at all: every factory's own
    CallbackData.filter() has already had its say by the time an update gets
    here, so whatever arrives is something no build-current button can produce.

    The spacer handler is registered globally even though the defect router
    would normally catch it first: one line makes the invariant unconditional,
    and the regression it prevents — a blank button wiping the employee list —
    is user-visible.

    The message handler is private-chat only: the support group carries traffic
    this bot is not meant to answer.
    """
    router = Router(name="stale")
    router.callback_query.register(noop_button, F.data == CB_NOOP)
    router.callback_query.register(stale_button)
    router.message.register(unhandled_message, F.chat.type == ChatType.PRIVATE)
    return router
