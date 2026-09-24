from aiogram import F, Router
from aiogram.filters import CommandStart

from apps.bot.callback_data import CB_LINK_CANCEL, LinkConfirmCB

from .start import cancel_link, confirm_link, start, start_with_link


def get_start_router() -> Router:
    """/start and the link buttons; first, so /start mid-flow leaves the flow alone."""
    router = Router(name="start")

    # Link first: a bare CommandStart() matches a deep link too
    router.message.register(start_with_link, CommandStart(deep_link=True))
    router.message.register(start, CommandStart())
    router.callback_query.register(confirm_link, LinkConfirmCB.filter())
    router.callback_query.register(cancel_link, F.data == CB_LINK_CANCEL)
    return router
