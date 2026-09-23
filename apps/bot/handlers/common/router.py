"""Routers for the handlers that are not part of any conversation.

Registration stays imperative, as it was under PTB — handlers are plain
functions with no decorators, which is what lets the tests call them directly.
"""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter

from apps.bot.callback_data import CB_LINK_CANCEL, CB_NOOP, LinkConfirmCB
from apps.bot.constants import BTN_HELP
from apps.bot.filters import PRIVATE_CHAT
from apps.bot.states import ALL_GROUPS

from .cancel import cancel
from .help import help_command
from .stale import noop_button, stale_button, unhandled_message
from .start import cancel_link, confirm_link, start, start_with_link


def get_start_router() -> Router:
    """/start and the account-link answer.

    Included before every conversation, which is what PTB's registration order
    did: /start mid-flow is answered here and leaves the flow standing.
    """
    router = Router(name="start")
    router.message.filter(PRIVATE_CHAT)
    # Link first: a bare CommandStart() matches a deep link too
    router.message.register(start_with_link, CommandStart(deep_link=True))
    router.message.register(start, CommandStart())
    router.callback_query.register(confirm_link, LinkConfirmCB.filter())
    router.callback_query.register(cancel_link, F.data == CB_LINK_CANCEL)
    return router


def get_cancel_router() -> Router:
    """/cancel alone, included right after start.

    Split out of get_help_router() so /cancel wins by registration order
    the way aiogram's own idioms expect, rather than depending on every
    conversation's free-text steps filtering it out with NotACommand. Ahead
    of every conversation router, so it can't be shadowed by a state-specific
    handler the way an unfiltered F.text one would.
    """
    router = Router(name="cancel")
    router.message.filter(PRIVATE_CHAT)
    router.message.register(cancel, Command("cancel"))
    return router


def get_help_router() -> Router:
    """/help.

    Included after the conversations, mirroring PTB's registration order: the
    Help menu button pressed inside the AI chat reaches that flow's own
    fallback, not help_command.
    """
    router = Router(name="help")
    router.message.filter(PRIVATE_CHAT)
    router.message.register(help_command, Command("help"))
    router.message.register(help_command, F.text == str(BTN_HELP))
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
    this bot is not meant to answer. It also stays out of every known state: a
    sticker at the photo step falls through here, and the step's own prompt is
    still on screen, so the form must survive untouched.
    """
    router = Router(name="stale")
    router.callback_query.register(noop_button, F.data == CB_NOOP)
    router.callback_query.register(stale_button)
    router.message.register(unhandled_message, PRIVATE_CHAT, ~StateFilter(*ALL_GROUPS))
    return router
