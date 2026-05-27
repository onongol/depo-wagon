import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.messages import BotMessages as M

logger = logging.getLogger(__name__)


async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available bot commands."""
    await update.message.reply_text(
        str(M.HELP_TEXT),
        parse_mode=M.PARSE_MODE,
    )
