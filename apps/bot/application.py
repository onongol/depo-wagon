import logging

from django.conf import settings
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from apps.bot.constants import BTN_HELP

logger = logging.getLogger(__name__)


def create_application() -> Application:
    """Build the Telegram Application and register all handlers."""
    from apps.bot.handlers.common import (
        cancel,
        error_handler,
        get_auth_handler,
        help_command,
    )
    from apps.bot.handlers.defect import get_defect_handler
    from apps.bot.handlers.tasks import get_tasks_handlers

    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .arbitrary_callback_data(True)
        .build()
    )

    # 1. /start + employee linking
    app.add_handler(get_auth_handler())

    # 2. Defect registration (8-step conversation)
    app.add_handler(get_defect_handler())

    # 3. Open defects list + pagination
    for handler in get_tasks_handlers():
        app.add_handler(handler)

    # 4. Utility commands
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(
        MessageHandler(filters.Text(str(BTN_HELP)), help_command)
    )
    app.add_handler(CommandHandler("cancel", cancel))

    app.add_error_handler(error_handler)

    logger.info("Bot application created with all handlers registered.")
    return app
