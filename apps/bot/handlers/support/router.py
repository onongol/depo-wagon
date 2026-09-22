"""Assembles the support handlers."""

from aiogram import F, Router
from aiogram.filters import Command, StateFilter

from apps.bot.filters import PRIVATE_CHAT, NotACommand
from apps.bot.handlers.common.cancel import cancel
from apps.bot.keyboards.menu import MENU_TEXTS
from apps.bot.states import SupportSG

from .admin_handlers import support_reply
from .user_handlers import support_receive, support_start
from .utils import support_chat_id


def get_support_router() -> Router:
    """The /support relay: user to the support group, and replies back.

    A menu button cancels, as in ai_chat: support sits ahead of the ai_chat and
    help routers, so it would otherwise be relayed as the question.

    The only router with a handler outside private chats, so PRIVATE_CHAT goes
    on each user-side handler rather than on the router. The reply half is
    registered only when a support chat is configured — an F.chat.id filter
    needs a concrete id. Replies to the bot's own messages reach it even with
    group privacy mode on.
    """
    router = Router(name="support")

    router.message.register(support_start, PRIVATE_CHAT, Command("support"))
    router.message.register(
        cancel, PRIVATE_CHAT, StateFilter(SupportSG.message), F.text.in_(MENU_TEXTS)
    )
    router.message.register(
        support_receive,
        PRIVATE_CHAT,
        StateFilter(SupportSG.message),
        F.text,
        ~F.text.in_(MENU_TEXTS),
        NotACommand(),
    )

    chat_id = support_chat_id()
    if chat_id is not None:
        router.message.register(
            support_reply,
            F.chat.id == chat_id,
            F.reply_to_message,
            NotACommand(),
        )

    return router
