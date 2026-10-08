"""Assembles the support handlers."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from django.conf import settings

from apps.bot.filters import NotACommand
from apps.bot.handlers.common.cancel import cancel
from apps.bot.keyboards.menu import MENU_TEXTS
from apps.bot.states import SupportSG

from .reply import support_reply
from .request import support_not_text, support_receive
from .start import support_start


def get_support_router() -> Router:
    """The user's half of /support: the question, relayed to the support group.

    A menu button cancels, as in ai_chat: support sits ahead of the ai_chat and
    help routers, so it would otherwise be relayed as the question.
    """
    router = Router(name="support")
    router.message.register(support_start, Command("support"))
    router.message.register(
        cancel, StateFilter(SupportSG.message), F.text.in_(MENU_TEXTS)
    )
    router.message.register(
        support_receive,
        StateFilter(SupportSG.message),
        F.text,
        ~F.text.in_(MENU_TEXTS),
        NotACommand(),
    )
    router.message.register(support_not_text, StateFilter(SupportSG.message), ~F.text)
    return router


def get_support_group_router() -> Router:
    """Operators' replies in the support group, relayed back to the user.

    Empty without a configured chat: F.chat.id needs a concrete id. Replies to
    the bot's own messages reach it even with group privacy mode on.
    """
    router = Router(name="support_group")
    chat_id = settings.TELEGRAM_SUPPORT_CHAT_ID
    if chat_id is not None:
        router.message.filter(F.chat.id == chat_id)
        router.message.register(support_reply, F.reply_to_message, NotACommand())
    return router
