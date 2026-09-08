from aiogram import F, Router
from aiogram.filters import Command, StateFilter

from apps.bot.constants import (
    BTN_ASK,
    BTN_CANCEL,
    BTN_HELP,
    BTN_NEW_DEFECT,
    BTN_OPEN_DEFECTS,
)
from apps.bot.filters import NotACommand
from apps.bot.handlers.common.cancel import cancel
from apps.bot.middlewares import AiChatTimeoutMiddleware
from apps.bot.states import AiChatSG

from .receive import ai_chat_receive
from .start import ai_chat_start

_MENU_TEXTS = {
    str(BTN_NEW_DEFECT),
    str(BTN_OPEN_DEFECTS),
    str(BTN_HELP),
    str(BTN_CANCEL),
    str(BTN_ASK),
}


def get_ai_chat_router() -> Router:
    """The /ask assistant session.

    A menu button pressed mid-session cancels rather than being answered as a
    question, which is what PTB's _MENU_TEXTS fallback did.
    """
    router = Router(name="ai_chat")
    router.message.outer_middleware(AiChatTimeoutMiddleware())

    router.message.register(ai_chat_start, Command("ask"))
    router.message.register(ai_chat_start, F.text == str(BTN_ASK))
    router.message.register(
        cancel, StateFilter(AiChatSG.chatting), F.text.in_(_MENU_TEXTS)
    )
    router.message.register(
        ai_chat_receive,
        StateFilter(AiChatSG.chatting),
        F.text,
        ~F.text.in_(_MENU_TEXTS),
        NotACommand(),
    )
    return router
