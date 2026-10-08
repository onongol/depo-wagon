from aiogram.utils.formatting import Text
from django.utils.translation import gettext_lazy as _


def build_ai_chat_thinking_text() -> Text:
    return Text("⏳ ", _("Thinking..."))


def build_ai_chat_error_text() -> Text:
    return Text("⚠️ ", _("Failed to get a response. Try rephrasing your question."))


def build_ai_chat_overloaded_text() -> Text:
    return Text(
        "⏱ ",
        _("The AI service is currently overloaded. Wait a few seconds and try again."),
    )


def build_ai_chat_blocked_text() -> Text:
    return Text(
        "⚠️ ",
        _("The response was blocked by safety filters. Please rephrase your question."),
    )
