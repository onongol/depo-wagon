from aiogram import F, Router
from aiogram.filters import Command, StateFilter

from apps.bot.constants import BTN_ASK
from apps.bot.filters import NotACommand
from apps.bot.handlers.common.cancel import cancel
from apps.bot.keyboards.menu import MENU_TEXTS
from apps.bot.states import AiChatSG

from .receive import ai_chat_receive
from .start import ai_chat_start


def get_ai_chat_router() -> Router:
    """The /ask assistant session.

    A menu button pressed mid-session cancels it instead of going to the model
    as a question.
    """
    router = Router(name="ai_chat")
    router.message.register(ai_chat_start, Command("ask"))
    router.message.register(ai_chat_start, F.text == str(BTN_ASK))
    router.message.register(
        cancel, StateFilter(AiChatSG.chatting), F.text.in_(MENU_TEXTS)
    )
    router.message.register(
        ai_chat_receive,
        StateFilter(AiChatSG.chatting),
        F.text,
        ~F.text.in_(MENU_TEXTS),
        NotACommand(),
    )
    return router
