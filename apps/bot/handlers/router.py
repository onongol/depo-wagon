from aiogram import Router

from apps.bot.filters import PRIVATE_CALLBACK, PRIVATE_CHAT


def _routers() -> list:
    """Every private-chat router, in the order updates reach them. Load-bearing:

    - start first, so the link buttons work mid-flow instead of hitting its catch-all;
    - cancel ahead of every conversation, so /cancel ends everything by order alone;
    - the defect entry ahead of support and ai_chat, so New Defect leaves them for a form;
    - tasks ahead of support and ai_chat, so Open Defects leaves them for the list;
    - support ahead of ai_chat and help, so their buttons cancel it, not get relayed;
    - help after the conversations, so Help inside the AI chat reaches its fallback;
    - stale last: it sees only what nothing else claimed.
    """
    from apps.bot.handlers.ai_chat.router import get_ai_chat_router
    from apps.bot.handlers.common.router import (
        get_cancel_router,
        get_help_router,
        get_stale_router,
    )
    from apps.bot.handlers.defect.router import (
        get_defect_entry_router,
        get_defect_flow_router,
    )
    from apps.bot.handlers.start.router import get_start_router
    from apps.bot.handlers.support.router import get_support_router
    from apps.bot.handlers.tasks.router import get_tasks_router

    return [
        get_start_router(),
        get_cancel_router(),
        get_defect_flow_router(),
        get_defect_entry_router(),
        get_tasks_router(),
        get_support_router(),
        get_ai_chat_router(),
        get_help_router(),
        get_stale_router(),
    ]


def get_private_router() -> Router:
    """Everything a private chat reaches. The chat-type filters sit here once.

    Callbacks too: no router puts buttons in a group, so a tap there is forged.
    """
    router = Router(name="private")
    router.message.filter(PRIVATE_CHAT)
    router.callback_query.filter(PRIVATE_CALLBACK)
    router.include_routers(*_routers())
    return router
