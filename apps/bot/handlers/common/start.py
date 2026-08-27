import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot import services
from apps.bot.constants import LinkStatus, UD_EMPLOYEE
from apps.bot.messages import BotMessages as M

from .utils import show_welcome_menu

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point, and the only place a Telegram account gets attached.

    Telegram passes the payload of a ``t.me/<bot>?start=<token>`` deep link as
    the argument to /start, which is how the web app hands this chat a token it
    issued for an already-authenticated employee. There is nothing to verify
    here: the web session established who they are before the token existed.

    A bare /start with no token is just "who am I" — an unattached chat is told
    to go and connect from the web app, because this bot cannot establish
    anybody's identity on its own.
    """
    telegram_id = update.effective_user.id
    token = context.args[0] if context.args else None

    if token:
        await _handle_link_token(update, context, token, telegram_id)
        return

    try:
        employee = await services.get_employee_by_telegram_id(telegram_id)
    except Exception:
        logger.exception("DB lookup failed for telegram_id=%s", telegram_id)
        await update.message.reply_text(str(M.SESSION_ERROR))
        return

    if employee:
        context.user_data[UD_EMPLOYEE] = employee
        await show_welcome_menu(update.message, employee)
        return

    await update.message.reply_text(
        str(M.NOT_CONNECTED).format(site_url=services.get_connect_url()),
        parse_mode=M.PARSE_MODE,
    )


async def _handle_link_token(update, context, token: str, telegram_id: int) -> None:
    try:
        employee, status = await services.link_telegram_by_token(token, telegram_id)
    except Exception:
        logger.exception("Telegram linking failed for telegram_id=%s", telegram_id)
        await update.message.reply_text(str(M.SESSION_ERROR))
        return

    if status is not LinkStatus.OK:
        text = {
            LinkStatus.INVALID_TOKEN: M.LINK_TOKEN_INVALID,
            LinkStatus.NO_EMPLOYEE: M.LINK_NO_EMPLOYEE,
            LinkStatus.ALREADY_LINKED: M.LINK_ALREADY_TAKEN,
        }[status]
        await update.message.reply_text(str(text), parse_mode=M.PARSE_MODE)
        return

    context.user_data[UD_EMPLOYEE] = employee
    await update.message.reply_text(str(M.LINK_OK), parse_mode=M.PARSE_MODE)
    await show_welcome_menu(update.message, employee)
