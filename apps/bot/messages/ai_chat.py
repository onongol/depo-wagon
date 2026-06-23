from django.utils.translation import gettext_lazy as _


class AiChatMessages:
    AI_CHAT_GREETING = _(
        "🤖 <b>AI Depot Assistant</b>\n\n"
        "I can answer questions about wagon maintenance, "
        "tolerance norms and depot documents.\n\n"
        "Type your question. To exit the chat — /cancel."
    )

    AI_CHAT_THINKING = _("⏳ Thinking...")

    AI_CHAT_ERROR = _("⚠️ Failed to get a response. Try rephrasing your question.")

    AI_CHAT_OVERLOADED = _(
        "⏱ The AI service is currently overloaded. Wait a few seconds and try again."
    )

    AI_CHAT_BLOCKED = _(
        "⚠️ The response was blocked by safety filters. Please rephrase your question."
    )

    AI_CHAT_NOT_AUTHENTICATED = _("⚠️ You are not registered. Please use /start.")
