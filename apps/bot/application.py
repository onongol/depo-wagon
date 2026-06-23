import logging

from django.conf import settings
from django.db import close_old_connections
from django.utils.translation import gettext_lazy as _
from telegram import BotCommand, MenuButtonCommands, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from apps.bot.constants import BTN_HELP
from apps.bot.messages import BotMessages as M

logger = logging.getLogger(__name__)

# Commands shown in the "/" menu and under the always-visible Menu button,
# so users have an entry point even when the START button is gone.
_BOT_COMMANDS = [
    BotCommand("start", _("Start")),
    BotCommand("new_defect", _("Register a defect")),
    BotCommand("my_tasks", _("Open defects")),
    BotCommand("ask", _("AI Assistant")),
    BotCommand("support", _("Ask the support team")),
    BotCommand("help", _("Help")),
    BotCommand("cancel", _("Cancel the current action")),
]


class _BotApplication(Application):
    async def process_update(self, update: Update) -> None:
        close_old_connections()
        await super().process_update(update)


async def _post_init(app: Application) -> None:
    """Publish commands, descriptions and the Menu button as stable entry points."""
    # Force lazy (gettext) strings to concrete str — Telegram serializes these
    # to JSON, and a lazy __proxy__ is not JSON-serializable.
    commands = [BotCommand(c.command, str(c.description)) for c in _BOT_COMMANDS]
    await app.bot.set_my_commands(commands)
    await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    await app.bot.set_my_description(str(M.BOT_DESCRIPTION))
    await app.bot.set_my_short_description(str(M.BOT_SHORT_DESCRIPTION))


def create_application() -> _BotApplication:
    """Build the Telegram Application and register all handlers."""
    from apps.bot.handlers.ai_chat import get_ai_chat_handler
    from apps.bot.handlers.common import (
        cancel,
        error_handler,
        get_auth_handler,
        help_command,
    )
    from apps.bot.handlers.defect import get_defect_handler
    from apps.bot.handlers.support import (
        get_support_handler,
        get_support_reply_handler,
    )
    from apps.bot.handlers.tasks import get_tasks_handlers

    app = (
        _BotApplication.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .arbitrary_callback_data(True)
        .post_init(_post_init)
        .build()
    )

    # 1. /start + employee linking
    app.add_handler(get_auth_handler())

    # 2. Defect registration (8-step conversation)
    app.add_handler(get_defect_handler())

    # 3. Open defects list + pagination
    for handler in get_tasks_handlers():
        app.add_handler(handler)

    # 4. Support relay (/support → support chat, and replies back to the user)
    app.add_handler(get_support_handler())
    support_reply_handler = get_support_reply_handler()
    if support_reply_handler is not None:
        app.add_handler(support_reply_handler)

    # 5. AI assistant chat (/ask)
    app.add_handler(get_ai_chat_handler())

    # 6. Utility commands
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Text(str(BTN_HELP)), help_command))
    app.add_handler(CommandHandler("cancel", cancel))

    app.add_error_handler(error_handler)

    logger.info("Bot application created with all handlers registered.")
    return app
