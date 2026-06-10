from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters

from apps.bot.states import AUTH_EMAIL, AUTH_OTP

from .cancel import cancel
from .email import receive_email
from .otp import receive_otp
from .start import start


def get_auth_handler() -> ConversationHandler:
    """Build and return the authentication ConversationHandler."""
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AUTH_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)
            ],
            AUTH_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_otp)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.ALL, cancel),
        ],
        name="auth",
        persistent=False,
    )
